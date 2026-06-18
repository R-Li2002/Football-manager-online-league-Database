from __future__ import annotations

import asyncio
from datetime import datetime, time as day_time, timedelta
from zoneinfo import ZoneInfo

from nonebot import get_bots, get_driver, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.params import EventPlainText
from nonebot.rule import to_me

from .config import BotSettings
from .heigo_api import HeigoApiClient
from .news_service import SeenNewsStore
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
seen_news_store = SeenNewsStore(settings.news_seen_store_path)

driver = get_driver()


@driver.on_shutdown
async def _close_clients() -> None:
    await api_client.aclose()
    await service.news_service.aclose()


def _next_run_at(hour: int, now: datetime) -> datetime:
    target = datetime.combine(now.date(), day_time(hour=hour), tzinfo=now.tzinfo)
    if target <= now:
        target += timedelta(days=1)
    return target


def _scheduled_targets(now: datetime) -> list[tuple[datetime, str]]:
    targets = [(_next_run_at(settings.news_daily_hour, now), "football_daily")]
    targets.extend((_next_run_at(hour, now), "football_news") for hour in settings.news_headline_hours)
    return targets


async def _send_scheduled_news(command_type: str) -> None:
    if not settings.news_broadcast_groups:
        return

    try:
        if command_type == "football_daily":
            items = await service.news_service.get_daily()
            fresh_items = seen_news_store.filter_new("dongqiudi_daily", items, settings.news_item_limit)
            text = service._format_news_items("懂球帝早报", fresh_items, settings.news_item_limit)
        else:
            items = await service.news_service.get_top_news()
            fresh_items = seen_news_store.filter_new("dongqiudi_top_news", items, settings.news_item_limit)
            text = service._format_news_items("懂球帝足球新闻", fresh_items, settings.news_item_limit)
    except Exception:
        return

    if not fresh_items:
        return

    bots = get_bots()
    if not bots:
        return
    bot = next(iter(bots.values()))
    message = MessageSegment.text(text)
    for group_id in settings.news_broadcast_groups:
        try:
            await bot.send_group_msg(group_id=int(group_id), message=message)
        except Exception:
            continue


async def _news_scheduler_loop() -> None:
    tz = ZoneInfo("Asia/Shanghai")
    while True:
        now = datetime.now(tz)
        target, command_type = min(_scheduled_targets(now), key=lambda item: item[0])
        await asyncio.sleep(max(1, (target - now).total_seconds()))
        await _send_scheduled_news(command_type)


@driver.on_startup
async def _start_news_scheduler() -> None:
    if settings.news_broadcast_groups:
        asyncio.create_task(_news_scheduler_loop())


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
            "news_broadcast_group_count": len(settings.news_broadcast_groups),
            "news_daily_hour": settings.news_daily_hour,
            "news_headline_hours": list(settings.news_headline_hours),
            "news_seen_store_path": settings.news_seen_store_path,
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
