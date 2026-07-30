from __future__ import annotations

from dataclasses import replace
from math import ceil
import re

from .config import BotSettings
from .models import CommandSpec, PlayerCommandResolution, ReplySpec
from .news_service import FootballNewsService, NewsItem
from .parser import parse_command


HELP_TEXT = (
    "可用命令:\n"
    "球员图 <名字或UID> [+1~+5]\n"
    "工资 <名字或UID>\n"
    "工资图 <名字或UID>\n"
    "名单 <球队名> [第N页]\n"
    "名单图 <球队名> [第N页]\n"
    "新闻 / 足球新闻\n"
    "早报 / 懂球帝早报\n"
    "\n"
    "示例:\n"
    "球员图 梅西\n"
    "球员图 梅西 +2\n"
    "工资图 贝林厄姆\n"
    "名单图 巴萨\n"
    "名单 巴萨 第2页\n"
    "新闻\n"
    "早报"
)

TEAM_ALIASES = {
    "A. Bilbao": ("athletic", "athleticclub", "athleticbilbao", "毕巴", "毕尔巴鄂", "毕尔巴鄂竞技"),
    "Associazione Sportiva Roma": ("asroma", "roma", "罗马", "罗马队"),
    "Aston Villa": ("villa", "avfc", "维拉", "阿斯顿维拉"),
    "Borussia Dortmund": ("bvb", "dortmund", "多特", "多特蒙德"),
    "Chelsea": ("cfc", "车子", "切尔西"),
    "FC Schalke 04": ("s04", "schalke", "沙尔克", "沙尔克04", "沙尔克零四"),
    "FLA": ("flamengo", "fla", "弗拉门戈"),
    "Inter": ("inter", "intermilan", "国米", "国际米兰"),
    "Juventus": ("juve", "尤文", "尤文图斯"),
    "Liverpool": ("lfc", "利物浦"),
    "Manchester City": ("mancity", "mc", "mcfc", "曼城", "曼彻斯特城", "曼城队"),
    "Manchester United": ("manutd", "manu", "mu", "mufc", "曼联", "曼彻斯特联", "曼彻斯特联队"),
    "Nottingham Forest": ("forest", "nffc", "诺丁汉森林", "诺丁汉"),
    "Olympique de Marseille": ("om", "marseille", "马赛", "马赛奥林匹克"),
    "R. Madrid": ("rm", "realmadrid", "皇马", "皇家马德里"),
    "Southampton": ("saints", "南安普顿"),
    "Sunderland": ("safc", "黑猫", "桑德兰"),
    "Tottenham Hotspur": ("spurs", "tot", "thfc", "热刺", "托特纳姆", "托特纳姆热刺"),
    "A. Madrid": ("atm", "atleti", "马竞", "马德里竞技"),
    "AC Milan": ("milan", "acm", "米兰", "ac米兰"),
    "Barcelona": ("barca", "fcb", "巴萨", "巴塞罗那"),
    "Bayer 04 Leverkusen": ("b04", "bayer04", "leverkusen", "药厂", "勒沃库森"),
    "Brighton & Hove Albion": ("bha", "brighton", "海鸥", "布莱顿", "布莱顿霍夫"),
    "Como 1907": ("como", "科莫", "科莫1907"),
    "Everton": ("efc", "太妃糖", "埃弗顿"),
    "FC Bayern München": ("bayern", "fcbayern", "拜仁", "拜仁慕尼黑"),
    "FK Bodø/Glimt": ("bodo", "glimt", "博德闪耀", "博德格林特"),
    "Leeds United": ("leeds", "利兹", "利兹联"),
    "Leicester City": ("lei", "lcfc", "foxes", "狐狸城", "莱斯特", "莱斯特城"),
    "Napoli": ("naples", "那不勒斯", "拿坡里"),
    "Olympique Lyonnais": ("ol", "lyon", "里昂", "里昂奥林匹克"),
    "Paris Saint-Germain": ("psg", "parissg", "巴黎", "大巴黎", "巴黎圣日耳曼"),
    "RB Leipzig": ("rbl", "莱比锡", "莱比锡红牛"),
    "Sport Lisboa e Benfica": ("slb", "benfica", "本菲卡"),
    "Sporting Clube de Portugal": ("scp", "sporting", "sportingcp", "葡体", "里斯本竞技", "葡萄牙体育"),
    "Wolverhampton Wanderers": ("wolves", "狼队", "伍尔弗汉普顿"),
    "AFC Ajax": ("ajax", "阿贾克斯"),
    "AFC Bournemouth": ("afcb", "bmouth", "bournemouth", "樱桃", "伯恩茅斯", "般尼茅夫"),
    "Arsenal": ("afc", "枪手", "阿森纳"),
    "Brentford": ("brentford", "蜜蜂", "布伦特福德"),
    "Club Atlético Boca Juniors": ("boca", "bocajuniors", "博卡", "博卡青年"),
    "Club Atlético Talleres de Córdoba": ("talleres", "塔勒雷斯", "科尔多瓦塔勒雷斯"),
    "Coventry City": ("coventry", "考文垂"),
    "Crystal Palace": ("cpfc", "水晶宫"),
    "Eintracht Frankfurt": ("frankfurt", "法兰克福", "法兰克福鹰"),
    "FC Heidenheim 1846": ("heidenheim", "海登海姆", "海登海姆1846"),
    "Feyenoord Rotterdam": ("feyenoord", "费耶诺德", "费耶诺德鹿特丹"),
    "Newcastle United": ("nufc", "newcastle", "纽卡", "纽卡斯尔", "纽卡斯尔联"),
    "Oriental Dragon": ("orientaldragon", "东方龙"),
    "RC Strasbourg Alsace": ("rcsa", "strasbourg", "斯特拉斯堡", "斯特拉斯堡阿尔萨斯"),
    "Sheffield United": ("sheffieldutd", "sheffutd", "谢菲联", "谢菲尔德联"),
    "Sportklub Sturm Graz": ("sturmgraz", "格拉茨风暴", "格拉茨"),
    "VfB Stuttgart": ("stuttgart", "斯图加特"),
    "West Ham United": ("whu", "whufc", "西汉姆", "西汉姆联"),
}

ROSTER_IMAGE_PAGE_SIZE = 20


class HeigoBotService:
    def __init__(self, api_client, signer, settings: BotSettings, news_service: FootballNewsService | None = None):
        self.api_client = api_client
        self.signer = signer
        self.settings = settings
        self.news_service = news_service or FootballNewsService(settings)

    async def handle_text(self, text: str) -> ReplySpec:
        command = parse_command(text)
        return await self.handle_command(command)

    async def handle_command(self, command: CommandSpec) -> ReplySpec:
        if command.command_type == "help":
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        if command.command_type == "player_image":
            return await self._handle_player_image(command)
        if command.command_type == "wage_text":
            return await self._handle_wage_text(command)
        if command.command_type == "wage_image":
            return await self._handle_wage_image(command)
        if command.command_type == "roster_text":
            return await self._handle_roster_text(command)
        if command.command_type == "roster_image":
            return await self._handle_roster_image(command)
        if command.command_type == "football_news":
            return await self._handle_football_news()
        if command.command_type == "football_daily":
            return await self._handle_football_daily()
        if command.command_type == "unknown":
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        return ReplySpec(reply_type="noop")

    @staticmethod
    def _format_news_items(title: str, items: list[NewsItem], limit: int) -> str:
        if not items:
            return f"{title}\n暂时没有读取到新闻。"
        lines = [title]
        for index, item in enumerate(items[:limit], start=1):
            published = f"（{item.published}）" if item.published else ""
            lines.append(f"{index}. {item.title}{published}\n{item.link}")
        return "\n\n".join(lines)

    async def _handle_football_news(self) -> ReplySpec:
        try:
            items = await self.news_service.get_top_news()
        except Exception as exc:
            return ReplySpec(reply_type="text", text=f"懂球帝新闻暂时读取失败：{type(exc).__name__}")
        text = self._format_news_items("懂球帝足球新闻", items, self.settings.news_item_limit)
        return ReplySpec(reply_type="text", text=text)

    async def _handle_football_daily(self) -> ReplySpec:
        try:
            items = await self.news_service.get_daily()
        except Exception as exc:
            return ReplySpec(reply_type="text", text=f"懂球帝早报暂时读取失败：{type(exc).__name__}")
        text = self._format_news_items("懂球帝早报", items, self.settings.news_item_limit)
        return ReplySpec(reply_type="text", text=text)

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

    async def resolve_player_command(self, command: CommandSpec) -> PlayerCommandResolution:
        """Resolve a player query while leaving conversation handling to the adapter."""
        if command.uid:
            return PlayerCommandResolution(command=command)

        keyword = (command.keyword or "").strip()
        if not keyword:
            return PlayerCommandResolution(error=ReplySpec(reply_type="text", text=HELP_TEXT))

        candidates = await self.api_client.search_player_attributes(keyword, version=command.version)
        if not candidates:
            return PlayerCommandResolution(
                error=ReplySpec(reply_type="text", text=f"未找到“{keyword}”相关球员。")
            )

        exact_matches = [
            item for item in candidates if str(item.get("name") or "").casefold() == keyword.casefold()
        ]
        if exact_matches:
            return PlayerCommandResolution(command=replace(command, uid=int(exact_matches[0]["uid"])))
        if len(candidates) == 1:
            return PlayerCommandResolution(command=replace(command, uid=int(candidates[0]["uid"])))
        return PlayerCommandResolution(candidates=tuple(candidates[:5]))

    async def _handle_player_image(self, command: CommandSpec) -> ReplySpec:
        detail, error = await self._resolve_player(command)
        if error:
            return error
        url = self.signer.build_player_png_url(
            int(detail["uid"]),
            version=command.version or detail.get("data_version"),
            step=command.step,
            theme=self.settings.bot_default_theme,
        )
        preview_label = f"成长预览 +{command.step}" if command.step > 0 else "当前属性"
        return ReplySpec(reply_type="image", text=f"{detail['name']} | UID {detail['uid']} | {preview_label}", image_url=url)

    async def _handle_wage_image(self, command: CommandSpec) -> ReplySpec:
        detail, error = await self._resolve_player(command)
        if error:
            return error
        await self.api_client.get_player_wage_detail(int(detail["uid"]))
        url = self.signer.build_wage_png_url(int(detail["uid"]), theme=self.settings.bot_default_theme)
        return ReplySpec(reply_type="image", text=f"{detail['name']} 工资图", image_url=url)

    @staticmethod
    def _format_decimal(value: object, *, digits: int = 2) -> str:
        return f"{float(value or 0):.{digits}f}"

    @staticmethod
    def _format_money(value: object) -> str:
        return f"{float(value or 0):.3f}M"

    @staticmethod
    def _format_slot_label(value: object) -> str:
        normalized = str(value or "").strip()
        return normalized if normalized else "-"

    async def _handle_wage_text(self, command: CommandSpec) -> ReplySpec:
        detail, error = await self._resolve_player(command)
        if error:
            return error

        wage_detail = await self.api_client.get_player_wage_detail(int(detail["uid"]))
        final_value = float(wage_detail.get("final_value") or 0)
        coefficient = float(wage_detail.get("coefficient") or 0)
        slot_type = str(wage_detail.get("slot_type") or "-")
        lines = [
            f"{detail['name']} | UID {detail['uid']}",
            f"位置 {detail.get('position') or '-'} | 年龄 {detail.get('age') or '-'} | HEIGO {detail.get('heigo_club') or '-'}",
            "工资计算：",
            f"初始值 {self._format_decimal(wage_detail.get('initial_value'))}",
            f"当前值 {self._format_decimal(wage_detail.get('current_value'))}",
            f"潜力值 {self._format_decimal(wage_detail.get('potential_value'))}",
            f"最终值 {self._format_decimal(final_value)}",
            f"初始字段 {self._format_decimal(wage_detail.get('initial_field'))}",
            f"名额档位 {slot_type}",
            f"工资系数 {self._format_decimal(coefficient)}",
            f"结果工资 {self._format_decimal(final_value)} × {self._format_decimal(coefficient)} = {self._format_money(wage_detail.get('wage'))}",
        ]
        return ReplySpec(reply_type="text", text="\n".join(lines))

    async def _handle_roster_image(self, command: CommandSpec) -> ReplySpec:
        team_name, error = await self._resolve_team_name(command.team_name or "")
        if error:
            return error
        if not team_name:
            return ReplySpec(reply_type="text", text=HELP_TEXT)
        players = await self.api_client.get_players_by_team(team_name)
        if not players:
            return ReplySpec(reply_type="text", text=f"未找到球队“{team_name}”的名单。")
        page, total_pages, _ = self._paginate_players(
            players,
            command.page,
            page_size=ROSTER_IMAGE_PAGE_SIZE,
        )
        url = self.signer.build_roster_png_url(team_name, page=page, theme=self.settings.bot_default_theme)
        return ReplySpec(reply_type="image", text=f"{team_name} 名单图 第 {page}/{total_pages} 页", image_url=url)

    async def _handle_roster_text(self, command: CommandSpec) -> ReplySpec:
        team_name, error = await self._resolve_team_name(command.team_name or "")
        if error:
            return error
        if not team_name:
            return ReplySpec(reply_type="text", text=HELP_TEXT)

        players = await self.api_client.get_players_by_team(team_name)
        if not players:
            return ReplySpec(reply_type="text", text=f"未找到球队“{team_name}”的名单。")

        page, total_pages, visible_players = self._paginate_players(players, command.page)
        start_index = (page - 1) * self.settings.bot_roster_page_size
        lines = [f"{team_name} 名单 第 {page}/{total_pages} 页，共 {len(players)} 人"]
        for index, player in enumerate(visible_players, start=start_index + 1):
            lines.append(
                f"{index}. {player.get('name', '-') } | {player.get('position', '-')} | "
                f"{player.get('age', '-')}岁 | CA/PA {player.get('ca', '-')} / {player.get('pa', '-')} | "
                f"工资 {self._format_money(player.get('wage'))} | 名额 {self._format_slot_label(player.get('slot_type'))}"
            )
        if page < total_pages:
            lines.append(f"发送“名单 {team_name} 第{page + 1}页”查看下一页。")
        return ReplySpec(reply_type="text", text="\n".join(lines))

    def _paginate_players(
        self,
        players: list[dict],
        requested_page: int | None,
        *,
        page_size: int | None = None,
    ) -> tuple[int, int, list[dict]]:
        page_size = max(1, int(page_size or self.settings.bot_roster_page_size or 20))
        total_pages = max(1, int(ceil(len(players) / page_size))) if players else 1
        page = max(1, min(total_pages, int(requested_page or 1)))
        start = (page - 1) * page_size
        return page, total_pages, players[start : start + page_size]

    @staticmethod
    def _normalize_team_key(value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (value or "").casefold())

    @classmethod
    def _build_team_alias_map(cls, team_names: list[str]) -> dict[str, str]:
        alias_map: dict[str, str] = {}
        for team_name in team_names:
            normalized = cls._normalize_team_key(team_name)
            if normalized:
                alias_map[normalized] = team_name
            for alias in TEAM_ALIASES.get(team_name, ()):
                alias_key = cls._normalize_team_key(alias)
                if alias_key:
                    alias_map[alias_key] = team_name
        return alias_map

    async def _resolve_team_name(self, raw_name: str) -> tuple[str | None, ReplySpec | None]:
        keyword = (raw_name or "").strip()
        if not keyword:
            return None, None

        teams = await self.api_client.get_teams()
        team_names = [str(team.get("name") or "").strip() for team in teams if str(team.get("name") or "").strip()]
        if not team_names:
            return keyword, None

        normalized_keyword = self._normalize_team_key(keyword)
        alias_map = self._build_team_alias_map(team_names)
        if normalized_keyword in alias_map:
            return alias_map[normalized_keyword], None

        partial_matches = [team_name for team_name in team_names if normalized_keyword and normalized_keyword in self._normalize_team_key(team_name)]
        if len(partial_matches) == 1:
            return partial_matches[0], None
        if len(partial_matches) > 1:
            shortlist = " / ".join(partial_matches[:5])
            return None, ReplySpec(reply_type="text", text=f"“{keyword}”匹配到多个球队。候选: {shortlist}")

        return keyword, None
