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
