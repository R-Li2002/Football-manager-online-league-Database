from __future__ import annotations

from collections.abc import Iterable

from nonebot.rule import to_me
from nonebot_plugin_alconna import Alconna, Args, MultiVar, on_alconna


COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    "球员图": ("球员",),
    "工资图": (),
    "工资": (),
    "名单图": (),
    "名单": (),
    "新闻": ("足球新闻", "懂球帝", "懂球帝新闻"),
    "早报": ("足球早报", "懂球帝早报"),
    "联赛日报": ("HEIGO日报", "heigo日报", "今日联赛"),
    "积分榜": ("联赛积分榜", "联赛排名"),
    "伤停": ("伤停榜", "伤停统计", "联赛伤停"),
    "排位榜": ("排位", "排位排行榜", "排位积分榜"),
    "球员榜": ("球员数据榜", "射手榜", "进球榜", "助攻榜", "最佳球员榜", "最佳榜", "MVP榜", "mvp榜"),
    "帮助": ("help",),
}

COMMAND_TYPES = {
    "球员图": "player_image",
    "工资图": "wage_image",
    "工资": "wage_text",
    "名单图": "roster_image",
    "名单": "roster_text",
    "新闻": "football_news",
    "早报": "football_daily",
    "联赛日报": "heigo_daily_report",
    "积分榜": "league_standings",
    "伤停": "league_suspensions",
    "排位榜": "rating_rankings",
    "球员榜": "player_rankings",
    "帮助": "help",
}


def create_command_matcher(command_name: str, aliases: Iterable[str] = ()):
    command = Alconna(command_name, Args["content", MultiVar(str, "*")])
    return on_alconna(
        command,
        aliases=set(aliases),
        rule=to_me(),
        auto_send_output=False,
        priority=10,
        block=True,
    )


def create_command_matchers() -> dict[str, type]:
    return {
        COMMAND_TYPES[name]: create_command_matcher(name, aliases)
        for name, aliases in COMMAND_ALIASES.items()
    }
