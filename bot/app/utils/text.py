from __future__ import annotations

import re


MENTION_PATTERN = re.compile(r"<@!?\d+>")
CQ_MENTION_PATTERN = re.compile(r"\[CQ:at,qq=\d+\]")
CQ_REPLY_PATTERN = re.compile(r"\[CQ:reply,id=[^\]]+\]")
DISPLAY_MENTION_PATTERN = re.compile(r"^(?:@[A-Za-z0-9_\-\u4e00-\u9fff]+|机器人)[\s:：]+")


def collapse_whitespace(text: str) -> str:
    return " ".join((text or "").strip().split())


def strip_robot_mentions(text: str) -> str:
    without_mentions = MENTION_PATTERN.sub(" ", text or "")
    without_cq_mentions = CQ_MENTION_PATTERN.sub(" ", without_mentions)
    without_cq_reply = CQ_REPLY_PATTERN.sub(" ", without_cq_mentions)
    without_display_mention = DISPLAY_MENTION_PATTERN.sub("", without_cq_reply.strip())
    return collapse_whitespace(without_display_mention)
