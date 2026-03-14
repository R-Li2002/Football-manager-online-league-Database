from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from repositories.attribute_repository import get_player_attribute_by_uid
from repositories.player_reaction_repository import (
    create_player_reaction_event,
    ensure_player_reaction_summary,
    get_latest_player_reaction_for_visitor,
    get_player_reaction_summary,
)
from schemas_read import PlayerReactionActionResponse, PlayerReactionSummaryResponse

REACTION_TYPES = {"flower", "egg"}
REACTION_COOLDOWN_SECONDS = 60


def _remaining_cooldown_seconds(latest_reaction_at: datetime | None, now: datetime) -> int:
    if latest_reaction_at is None:
        return 0
    available_at = latest_reaction_at + timedelta(seconds=REACTION_COOLDOWN_SECONDS)
    remaining = int((available_at - now).total_seconds())
    return max(0, remaining)


def build_player_reaction_summary(
    db: Session,
    player_uid: int,
    visitor_token: str | None = None,
    now: datetime | None = None,
) -> PlayerReactionSummaryResponse:
    current_time = now or datetime.now()
    summary = get_player_reaction_summary(db, player_uid)
    latest_reaction = (
        get_latest_player_reaction_for_visitor(db, player_uid, visitor_token)
        if visitor_token
        else None
    )
    cooldown_seconds = _remaining_cooldown_seconds(
        latest_reaction.created_at if latest_reaction else None,
        current_time,
    )
    next_available_at = (
        latest_reaction.created_at + timedelta(seconds=REACTION_COOLDOWN_SECONDS)
        if latest_reaction and cooldown_seconds > 0
        else None
    )
    return PlayerReactionSummaryResponse(
        flowers=summary.flowers if summary else 0,
        eggs=summary.eggs if summary else 0,
        can_react=cooldown_seconds == 0,
        cooldown_seconds=cooldown_seconds,
        next_available_at=next_available_at,
    )


def record_player_reaction(
    db: Session,
    player_uid: int,
    visitor_token: str,
    reaction_type: str,
    now: datetime | None = None,
) -> PlayerReactionActionResponse:
    if reaction_type not in REACTION_TYPES:
        raise HTTPException(status_code=400, detail="不支持的互动类型。")

    current_time = now or datetime.now()
    if not get_player_attribute_by_uid(db, player_uid):
        raise HTTPException(status_code=404, detail="找不到球员信息。")

    latest_reaction = get_latest_player_reaction_for_visitor(db, player_uid, visitor_token)
    cooldown_seconds = _remaining_cooldown_seconds(
        latest_reaction.created_at if latest_reaction else None,
        current_time,
    )
    if cooldown_seconds > 0:
        return PlayerReactionActionResponse(
            accepted=False,
            reaction_type=reaction_type,
            message=f"请等待 {cooldown_seconds} 秒后再互动。",
            summary=build_player_reaction_summary(
                db,
                player_uid,
                visitor_token=visitor_token,
                now=current_time,
            ),
        )

    summary = ensure_player_reaction_summary(db, player_uid)
    if reaction_type == "flower":
        summary.flowers += 1
        success_message = "送花成功。"
    else:
        summary.eggs += 1
        success_message = "踩鸡蛋成功。"
    summary.updated_at = current_time

    create_player_reaction_event(
        db,
        player_uid=player_uid,
        visitor_token=visitor_token,
        reaction_type=reaction_type,
        created_at=current_time,
    )
    db.commit()

    return PlayerReactionActionResponse(
        accepted=True,
        reaction_type=reaction_type,
        message=success_message,
        summary=build_player_reaction_summary(
            db,
            player_uid,
            visitor_token=visitor_token,
            now=current_time,
        ),
    )
