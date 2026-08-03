from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from nonebot import get_bots, get_driver, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import EventPlainText
from nonebot.rule import to_me
from nonebot_plugin_waiter import waiter

from .command_schema import create_command_matchers
from .config import BotSettings
from .heigo_api import HeigoApiClient
from .models import CommandSpec, ReplySpec
from .news_service import SeenNewsStore
from .parser import parse_command
from .rate_limit import InMemoryRateLimiter
from .scheduling import (
    DAILY_REPORT_BROADCAST_JOB,
    DAILY_REPORT_REFRESH_JOB,
    execute_daily_report_job,
    scheduled_targets,
)
from .service import HeigoBotService
from .signer import RenderUrlSigner


settings = BotSettings.from_env()
api_client = HeigoApiClient(settings.heigo_base_url, render_base_url=settings.heigo_render_base_url)
signer = RenderUrlSigner(
    render_base_url=settings.heigo_render_base_url,
    signing_key=settings.internal_render_signing_key,
    ttl_seconds=settings.heigo_render_ttl_seconds,
    theme=settings.bot_default_theme,
)
rate_limiter = InMemoryRateLimiter()
service = HeigoBotService(api_client, signer, settings)
seen_news_store = SeenNewsStore(settings.news_seen_store_path)
logger = logging.getLogger(__name__)

driver = get_driver()


@driver.on_shutdown
async def _close_clients() -> None:
    await api_client.aclose()
    await service.news_service.aclose()


def _scheduled_targets(now: datetime) -> list[tuple[datetime, str]]:
    return scheduled_targets(
        now,
        news_daily_hour=settings.news_daily_hour,
        news_headline_hours=settings.news_headline_hours,
        include_daily_report=bool(settings.heigo_daily_report_groups),
        daily_report_broadcast_hour=settings.heigo_daily_report_broadcast_hour,
        daily_report_refresh_hour=settings.heigo_daily_report_refresh_hour,
    )


async def _broadcast_daily_report(report: dict, report_date: str) -> None:
    bots = get_bots()
    if not bots:
        return
    bot = next(iter(bots.values()))
    fingerprint = str(report.get("fingerprint") or "").strip()
    title = str(report.get("title") or "HEIGO 联赛日报").strip()
    focus_content = str(report.get("focus_content") or report.get("content") or "昨日暂无可播报内容。").strip()
    image_url = api_client.get_daily_report_image_url(report_date, fingerprint, focus_only=True)
    fallback_text = f"{title}\n\n{focus_content}"
    marker_link = f"heigo-daily:{report_date}"

    for group_id in settings.heigo_daily_report_groups:
        feed_key = f"heigo_daily_report:{group_id}"
        if seen_news_store.has_seen(feed_key, marker_link):
            continue
        message = Message()
        message += MessageSegment.text(f"{title}\n")
        message += MessageSegment.image(image_url)
        sent = False
        try:
            await bot.send_group_msg(group_id=int(group_id), message=message)
            sent = True
        except Exception:
            try:
                await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.text(fallback_text))
                sent = True
            except Exception:
                logger.exception("Failed to broadcast HEIGO daily report date=%s group=%s", report_date, group_id)
        if sent:
            seen_news_store.mark_seen(feed_key, marker_link)


async def _warm_daily_report_image(report_date: str, fingerprint: str) -> None:
    cache_status = await api_client.warm_daily_report_image(report_date, fingerprint, focus_only=True)
    logger.info("Refreshed HEIGO daily report date=%s image_cache=%s", report_date, cache_status)


async def _run_daily_report_job(command_type: str, now: datetime) -> None:
    report = await execute_daily_report_job(
        command_type,
        now,
        get_report=api_client.get_daily_report,
        warm_image=_warm_daily_report_image,
        broadcast=_broadcast_daily_report,
    )
    if command_type == DAILY_REPORT_BROADCAST_JOB:
        logger.info(
            "Broadcast HEIGO daily report date=%s groups=%s",
            report.get("report_date"),
            len(settings.heigo_daily_report_groups),
        )


async def _send_scheduled_news(command_type: str) -> None:
    target_groups = settings.news_broadcast_groups
    if not target_groups:
        return

    image_url = ""
    fallback_text = ""
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
    for group_id in target_groups:
        message = Message()
        message += MessageSegment.text(f"{text}\n" if image_url else text)
        if image_url:
            message += MessageSegment.image(image_url)
        try:
            await bot.send_group_msg(group_id=int(group_id), message=message)
        except Exception:
            if image_url:
                try:
                    await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.text(fallback_text or text))
                except Exception:
                    continue


async def _news_scheduler_loop() -> None:
    tz = ZoneInfo("Asia/Shanghai")
    while True:
        now = datetime.now(tz)
        target, command_type = min(_scheduled_targets(now), key=lambda item: item[0])
        await asyncio.sleep(max(1, (target - now).total_seconds()))
        run_at = datetime.now(tz)
        try:
            if command_type in {DAILY_REPORT_BROADCAST_JOB, DAILY_REPORT_REFRESH_JOB}:
                await _run_daily_report_job(command_type, run_at)
            else:
                await _send_scheduled_news(command_type)
        except Exception:
            logger.exception("Scheduled bot job failed: %s", command_type)


@driver.on_startup
async def _start_news_scheduler() -> None:
    if settings.news_broadcast_groups or settings.heigo_daily_report_groups:
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
            "heigo_daily_report_group_count": len(settings.heigo_daily_report_groups),
            "heigo_daily_report_broadcast_hour": settings.heigo_daily_report_broadcast_hour,
            "heigo_daily_report_refresh_hour": settings.heigo_daily_report_refresh_hour,
        }


def _is_request_allowed(event: MessageEvent) -> bool:
    if isinstance(event, GroupMessageEvent) and not settings.is_group_allowed(str(event.group_id)):
        return False

    user_id = str(getattr(event, "user_id", "") or "")
    if user_id:
        allowed, _ = rate_limiter.check_user_cooldown(f"user:{user_id}", settings.bot_user_cooldown_seconds)
        if not allowed:
            return False

    if isinstance(event, GroupMessageEvent):
        allowed, _ = rate_limiter.check_group_window(
            f"group:{event.group_id}",
            settings.bot_group_limit_per_minute,
        )
        if not allowed:
            return False
    return True


async def _send_reply(event_matcher: type[Matcher], event: MessageEvent, reply: ReplySpec) -> None:
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

    try:
        await event_matcher.send(message)
    except Exception:
        if reply.reply_type == "image" and reply.text:
            await event_matcher.send(MessageSegment.text(reply.fallback_text or reply.text))
            return
        raise


def _candidate_prompt(keyword: str, candidates: tuple[dict, ...]) -> str:
    lines = [f"“{keyword}”匹配到多个球员，请回复序号选择（30 秒内有效）："]
    for index, candidate in enumerate(candidates, start=1):
        name = str(candidate.get("name") or "未知球员")
        uid = str(candidate.get("uid") or "-")
        club = str(candidate.get("heigo_club") or candidate.get("club") or "").strip()
        suffix = f" | {club}" if club else ""
        lines.append(f"{index}. {name} | UID {uid}{suffix}")
    lines.append("回复“取消”可结束选择。")
    return "\n".join(lines)


async def _resolve_ambiguous_player(
    event_matcher: type[Matcher],
    command: CommandSpec,
) -> tuple[CommandSpec | None, ReplySpec | None]:
    resolution = await service.resolve_player_command(command)
    if resolution.error:
        return None, resolution.error
    if resolution.command:
        return resolution.command, None

    candidates = resolution.candidates

    @waiter(["message"], matcher=event_matcher, keep_session=True, block=True)
    async def wait_for_choice(event: MessageEvent) -> str:
        return event.get_plaintext().strip()

    prompt = _candidate_prompt(command.keyword, candidates)
    for attempt in range(3):
        before = prompt if attempt == 0 else f"请输入 1-{len(candidates)} 的序号，或回复“取消”。"
        answer = await wait_for_choice.wait(before, timeout=30)
        if answer is None:
            return None, ReplySpec(reply_type="text", text="选择已超时，请重新发送原命令。")
        normalized = answer.strip()
        if normalized in {"取消", "cancel", "退出"}:
            return None, ReplySpec(reply_type="text", text="已取消球员选择。")
        if normalized.isdigit():
            selected_index = int(normalized) - 1
            if 0 <= selected_index < len(candidates):
                selected_uid = int(candidates[selected_index]["uid"])
                return replace(command, uid=selected_uid), None

    return None, ReplySpec(reply_type="text", text="输入次数过多，已结束选择，请重新发送原命令。")


async def _handle_command_message(
    event_matcher: type[Matcher],
    event: MessageEvent,
    plain_text: str,
) -> None:
    if not _is_request_allowed(event):
        return

    command = parse_command(plain_text)
    if command.command_type in {"player_image", "wage_text", "wage_image"}:
        command, error = await _resolve_ambiguous_player(event_matcher, command)
        if error:
            await _send_reply(event_matcher, event, error)
            return
        if command is None:
            return

    reply = await service.handle_command(command)
    await _send_reply(event_matcher, event, reply)


command_matchers = create_command_matchers()


def _register_command_handler(command_matcher: type[Matcher]) -> None:
    @command_matcher.handle()
    async def _(event: MessageEvent, plain_text: str = EventPlainText()):
        await _handle_command_message(command_matcher, event, plain_text)


for _command_matcher in command_matchers.values():
    _register_command_handler(_command_matcher)


fallback_matcher = on_message(rule=to_me(), priority=20, block=False)


@fallback_matcher.handle()
async def _(event: MessageEvent, plain_text: str = EventPlainText()):
    await _handle_command_message(fallback_matcher, event, plain_text)
