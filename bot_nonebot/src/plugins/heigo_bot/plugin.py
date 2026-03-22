from __future__ import annotations

from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.params import EventPlainText
from nonebot.rule import to_me

from .config import BotSettings
from .heigo_api import HeigoApiClient
from .rate_limit import InMemoryRateLimiter
from .service import HeigoBotService
from .signer import RenderUrlSigner


settings = BotSettings.from_env()
api_client = HeigoApiClient(settings.heigo_base_url)
signer = RenderUrlSigner(
    render_base_url=settings.heigo_render_base_url,
    signing_key=settings.internal_render_signing_key,
    ttl_seconds=settings.heigo_render_ttl_seconds,
    theme=settings.bot_default_theme,
)
rate_limiter = InMemoryRateLimiter()
service = HeigoBotService(api_client, signer, settings)

driver = get_driver()


@driver.on_shutdown
async def _close_clients() -> None:
    await api_client.aclose()


if hasattr(driver, "server_app"):
    @driver.server_app.get("/health")
    async def _health():
        heigo_status = "ok"
        try:
            await api_client.get_health()
        except Exception as exc:  # pragma: no cover - runtime integration check
            heigo_status = type(exc).__name__
        return {
            "status": "ok" if heigo_status == "ok" else "degraded",
            "heigo_api": heigo_status,
            "render_signing_key_configured": bool(settings.internal_render_signing_key),
            "allow_all_groups": settings.qq_bot_allow_all_groups,
            "allowed_group_count": len(settings.qq_bot_allowed_groups),
        }


matcher = on_message(rule=to_me(), priority=10, block=False)


@matcher.handle()
async def _(bot: Bot, event: MessageEvent, plain_text: str = EventPlainText()):
    if isinstance(event, GroupMessageEvent) and not settings.is_group_allowed(str(event.group_id)):
        return

    user_id = str(getattr(event, "user_id", "") or "")
    if user_id:
        allowed, _ = rate_limiter.check_user_cooldown(f"user:{user_id}", settings.bot_user_cooldown_seconds)
        if not allowed:
            return

    if isinstance(event, GroupMessageEvent):
        allowed, _ = rate_limiter.check_group_window(
            f"group:{event.group_id}",
            settings.bot_group_limit_per_minute,
        )
        if not allowed:
            return

    reply = await service.handle_text(plain_text)
    if reply.reply_type == "noop":
        return

    message = Message()
    if getattr(event, "message_id", None):
        message += MessageSegment.reply(event.message_id)

    if reply.reply_type == "image":
        if reply.text:
            message += MessageSegment.text(f"{reply.text}\n")
        message += MessageSegment.image(reply.image_url)
    else:
        message += MessageSegment.text(reply.text)

    await matcher.send(message)
