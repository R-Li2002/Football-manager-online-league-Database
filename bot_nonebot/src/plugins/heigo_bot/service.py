from __future__ import annotations

from .config import BotSettings
from .models import CommandSpec, ReplySpec
from .parser import parse_command


HELP_TEXT = (
    "可用命令:\n"
    "球员图 <名字或UID> [版本v2026-03]\n"
    "工资图 <名字或UID>\n"
    "名单图 <球队名> [第2页]"
)


class HeigoBotService:
    def __init__(self, api_client, signer, settings: BotSettings):
        self.api_client = api_client
        self.signer = signer
        self.settings = settings

    async def handle_text(self, text: str) -> ReplySpec:
        command = parse_command(text)
        return await self.handle_command(command)

    async def handle_command(self, command: CommandSpec) -> ReplySpec:
        if command.command_type == "help":
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        if command.command_type == "player_image":
            return await self._handle_player_image(command)
        if command.command_type == "wage_image":
            return await self._handle_wage_image(command)
        if command.command_type == "roster_image":
            return await self._handle_roster_image(command)
        if command.command_type == "unknown":
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        return ReplySpec(reply_type="noop")

    async def _resolve_player(self, command: CommandSpec) -> tuple[dict | None, ReplySpec | None]:
        if command.uid:
            detail = await self.api_client.get_player_attribute_detail(command.uid, version=command.version)
            if not detail:
                return None, ReplySpec(reply_type="text", text=f"未找到 UID {command.uid} 对应球员。")
            return detail, None

        keyword = (command.keyword or "").strip()
        if not keyword:
            return None, ReplySpec(reply_type="text", text=HELP_TEXT)

        candidates = await self.api_client.search_player_attributes(keyword, version=command.version)
        if not candidates:
            return None, ReplySpec(reply_type="text", text=f"未找到“{keyword}”相关球员。")

        exact_matches = [item for item in candidates if str(item.get("name") or "").casefold() == keyword.casefold()]
        selected = exact_matches[0] if len(exact_matches) == 1 else candidates[0]
        if len(exact_matches) == 0 and len(candidates) > 1:
            shortlist = " / ".join(f"{item.get('name')}({item.get('uid')})" for item in candidates[:5])
            return None, ReplySpec(reply_type="text", text=f"“{keyword}”匹配到多个球员，请改用 UID。候选: {shortlist}")

        detail = await self.api_client.get_player_attribute_detail(int(selected["uid"]), version=command.version)
        if not detail:
            return None, ReplySpec(reply_type="text", text=f"球员 {selected.get('name')} 详情读取失败。")
        return detail, None

    async def _handle_player_image(self, command: CommandSpec) -> ReplySpec:
        detail, error = await self._resolve_player(command)
        if error:
            return error
        url = self.signer.build_player_png_url(
            int(detail["uid"]),
            version=command.version or detail.get("data_version"),
            theme=self.settings.bot_default_theme,
        )
        return ReplySpec(reply_type="image", text=f"{detail['name']} | UID {detail['uid']}", image_url=url)

    async def _handle_wage_image(self, command: CommandSpec) -> ReplySpec:
        detail, error = await self._resolve_player(command)
        if error:
            return error
        await self.api_client.get_player_wage_detail(int(detail["uid"]))
        url = self.signer.build_wage_png_url(int(detail["uid"]), theme=self.settings.bot_default_theme)
        return ReplySpec(reply_type="image", text=f"{detail['name']} 工资图", image_url=url)

    async def _handle_roster_image(self, command: CommandSpec) -> ReplySpec:
        team_name = (command.team_name or "").strip()
        if not team_name:
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        players = await self.api_client.get_players_by_team(team_name)
        if not players:
            return ReplySpec(reply_type="text", text=f"未找到球队“{team_name}”的名单。")
        total_pages = max(1, (len(players) + self.settings.bot_roster_page_size - 1) // self.settings.bot_roster_page_size)
        page = max(1, min(total_pages, command.page or 1))
        url = self.signer.build_roster_png_url(team_name, page=page, theme=self.settings.bot_default_theme)
        return ReplySpec(reply_type="image", text=f"{team_name} 名单图 第 {page}/{total_pages} 页", image_url=url)
