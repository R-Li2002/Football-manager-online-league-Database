from __future__ import annotations

from typing import Any

from app.clients.heigo_client import HeigoClient
from app.config import BotSettings
from app.schemas.bot_commands import BotCommand, PreparedReply
from app.services.render_service import PlayerShareRenderService


def _format_player_summary(detail: dict[str, Any]) -> str:
    return (
        f"{detail.get('name', '-')}\n"
        f"UID: {detail.get('uid', '-')}\n"
        f"位置: {detail.get('position', '-')}\n"
        f"年龄: {detail.get('age', '-')}\n"
        f"CA/PA: {detail.get('ca', '-')} / {detail.get('pa', '-')}\n"
        f"HEIGO: {detail.get('heigo_club', '-')}\n"
        f"现实俱乐部: {detail.get('club', '-')}"
    )


def _format_candidate_list(title: str, rows: list[dict[str, Any]], limit: int = 5) -> str:
    lines = [title]
    for row in rows[:limit]:
        lines.append(
            f"- {row.get('name', '-')} | UID {row.get('uid', '-')} | {row.get('position', '-')} | {row.get('heigo_club', row.get('team_name', '-'))}"
        )
    return "\n".join(lines)


async def _resolve_player_uid(client: HeigoClient, command: BotCommand) -> tuple[int | None, list[dict[str, Any]]]:
    if command.uid is not None:
        return command.uid, []

    if not command.keyword:
        return None, []

    candidates = await client.search_player_attributes(command.keyword, version=command.version)
    if not candidates:
        players = await client.search_players(command.keyword)
        candidates = [
            {
                "uid": player.get("uid"),
                "name": player.get("name"),
                "position": player.get("position"),
                "heigo_club": player.get("team_name"),
            }
            for player in players
        ]

    if len(candidates) == 1:
        return int(candidates[0]["uid"]), candidates

    exact_matches = [
        row
        for row in candidates
        if str(row.get("name", "")).strip().lower() == command.keyword.strip().lower()
    ]
    if len(exact_matches) == 1:
        return int(exact_matches[0]["uid"]), candidates

    return None, candidates


async def build_reply(
    command: BotCommand,
    client: HeigoClient,
    settings: BotSettings,
    render_service: PlayerShareRenderService | None = None,
) -> PreparedReply:
    if command.command_type in {"help", "unknown"}:
        return PreparedReply(
            reply_type="text",
            text=(
                "可用命令：\n"
                "@机器人 球员 梅西\n"
                "@机器人 球员图 梅西\n"
                "@机器人 名单 Barcelona\n"
                "@机器人 工资 24048100\n"
                "@机器人 帮助"
            ),
        )

    if command.command_type == "player":
        uid, candidates = await _resolve_player_uid(client, command)
        if uid is None:
            if candidates:
                return PreparedReply(reply_type="text", text=_format_candidate_list("找到多个候选，请改用 UID：", candidates))
            return PreparedReply(reply_type="text", text=f"未找到球员：{command.keyword or '空查询'}")

        detail = await client.get_player_attribute_detail(uid, version=command.version)
        if not detail:
            return PreparedReply(reply_type="text", text=f"未找到 UID {uid} 的球员详情")
        return PreparedReply(reply_type="text", text=_format_player_summary(detail))

    if command.command_type == "player_image":
        uid, candidates = await _resolve_player_uid(client, command)
        if uid is None:
            if candidates:
                return PreparedReply(reply_type="text", text=_format_candidate_list("找到多个候选，请改用 UID 生成球员图：", candidates))
            return PreparedReply(reply_type="text", text=f"未找到球员：{command.keyword or '空查询'}")

        detail = await client.get_player_attribute_detail(uid, version=command.version)
        if not detail:
            return PreparedReply(reply_type="text", text=f"未找到 UID {uid} 的球员详情")

        if render_service is None:
            return PreparedReply(reply_type="text", text="图片渲染服务未启用")

        try:
            share_url, rendered = await render_service.render_player_share(
                uid=uid,
                player_name=detail.get("name", str(uid)),
                version=command.version or detail.get("data_version"),
                step=command.step,
            )
            return PreparedReply(
                reply_type="image",
                text=f"{detail.get('name', uid)} 球员图",
                meta={
                    "uid": uid,
                    "share_url": share_url,
                    "image_path": rendered.file_path,
                    "image_name": rendered.file_name,
                    "mime_type": rendered.mime_type,
                    "fallback_text": (
                        f"{detail.get('name', uid)} 球员图发送失败，已降级为文本。\n"
                        f"分享页：{share_url}"
                    ),
                },
            )
        except Exception as exc:
            return PreparedReply(
                reply_type="text",
                text=(
                    f"球员图生成失败：{detail.get('name', uid)}\n"
                    f"错误：{type(exc).__name__}\n"
                    "请检查 Playwright 依赖、浏览器运行时和内部分享页可访问性。"
                ),
                meta={"uid": uid, "error": str(exc)},
            )

    if command.command_type == "roster":
        if not command.team_name:
            return PreparedReply(reply_type="text", text="请提供球队名，例如：@机器人 名单 Barcelona")

        players = await client.get_players_by_team(command.team_name)
        if not players:
            return PreparedReply(reply_type="text", text=f"未找到球队或名单为空：{command.team_name}")

        page_size = 15
        start = (command.page - 1) * page_size
        selected = players[start : start + page_size]
        if not selected:
            return PreparedReply(reply_type="text", text=f"{command.team_name} 第 {command.page} 页没有数据")

        lines = [f"{command.team_name} 名单 第 {command.page} 页"]
        for player in selected:
            lines.append(
                f"- {player.get('name', '-')} | UID {player.get('uid', '-')} | {player.get('position', '-')} | CA/PA {player.get('ca', '-')} / {player.get('pa', '-')}"
            )
        return PreparedReply(reply_type="text", text="\n".join(lines))

    if command.command_type == "wage":
        uid, candidates = await _resolve_player_uid(client, command)
        if uid is None:
            if candidates:
                return PreparedReply(reply_type="text", text=_format_candidate_list("找到多个候选，请改用 UID 查询工资：", candidates))
            return PreparedReply(reply_type="text", text=f"未找到球员：{command.keyword or '空查询'}")

        detail = await client.get_player_attribute_detail(uid, version=command.version)
        if not detail:
            return PreparedReply(reply_type="text", text=f"未找到 UID {uid} 的球员详情")
        wage = await client.get_player_wage_detail(uid)
        return PreparedReply(
            reply_type="text",
            text=(
                f"{detail.get('name', uid)} 工资详情\n"
                f"UID: {uid}\n"
                f"槽位: {wage.get('slot_type', '-')}\n"
                f"系数: {wage.get('coefficient', '-')}\n"
                f"初始值: {wage.get('initial_value', '-')}\n"
                f"当前值: {wage.get('current_value', '-')}\n"
                f"潜力值: {wage.get('potential_value', '-')}\n"
                f"最终值: {wage.get('final_value', '-')}\n"
                f"工资: {wage.get('wage', '-')}"
            ),
        )

    return PreparedReply(reply_type="text", text="暂不支持该命令")
