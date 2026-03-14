from datetime import datetime

from sqlalchemy.orm import Session

from models import PlayerReactionEvent, PlayerReactionSummary


def get_player_reaction_summary(db: Session, player_uid: int) -> PlayerReactionSummary | None:
    return db.query(PlayerReactionSummary).filter(PlayerReactionSummary.player_uid == player_uid).first()


def ensure_player_reaction_summary(db: Session, player_uid: int) -> PlayerReactionSummary:
    summary = get_player_reaction_summary(db, player_uid)
    if summary:
        return summary

    summary = PlayerReactionSummary(player_uid=player_uid, flowers=0, eggs=0)
    db.add(summary)
    db.flush()
    return summary


def get_latest_player_reaction_for_visitor(db: Session, player_uid: int, visitor_token: str) -> PlayerReactionEvent | None:
    return (
        db.query(PlayerReactionEvent)
        .filter(
            PlayerReactionEvent.player_uid == player_uid,
            PlayerReactionEvent.visitor_token == visitor_token,
        )
        .order_by(PlayerReactionEvent.created_at.desc(), PlayerReactionEvent.id.desc())
        .first()
    )


def create_player_reaction_event(
    db: Session,
    player_uid: int,
    visitor_token: str,
    reaction_type: str,
    created_at: datetime,
) -> PlayerReactionEvent:
    event = PlayerReactionEvent(
        player_uid=player_uid,
        visitor_token=visitor_token,
        reaction_type=reaction_type,
        created_at=created_at,
    )
    db.add(event)
    db.flush()
    return event
