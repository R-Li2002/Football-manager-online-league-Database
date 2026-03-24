from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import Player, PlayerAttribute, PlayerAttributeVersion, PlayerReactionEvent, PlayerReactionSummary


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


def list_player_reaction_leaderboard_rows(
    db: Session,
    *,
    attribute_model: type[PlayerAttribute] | type[PlayerAttributeVersion],
    data_version: str | None = None,
    metric: str = "flowers",
    team_name: str | None = None,
    limit: int = 20,
):
    net_score = (PlayerReactionSummary.flowers - PlayerReactionSummary.eggs).label("net_score")
    total_reactions = (PlayerReactionSummary.flowers + PlayerReactionSummary.eggs).label("total_reactions")

    query = (
        db.query(
            attribute_model.uid.label("uid"),
            attribute_model.name.label("name"),
            attribute_model.position.label("position"),
            attribute_model.age.label("age"),
            attribute_model.ca.label("ca"),
            attribute_model.pa.label("pa"),
            Player.team_name.label("heigo_club"),
            PlayerReactionSummary.flowers.label("flowers"),
            PlayerReactionSummary.eggs.label("eggs"),
            net_score,
            total_reactions,
            PlayerReactionSummary.updated_at.label("updated_at"),
        )
        .join(PlayerReactionSummary, PlayerReactionSummary.player_uid == attribute_model.uid)
        .outerjoin(Player, Player.uid == attribute_model.uid)
    )

    if attribute_model is PlayerAttributeVersion and data_version:
        query = query.filter(PlayerAttributeVersion.data_version == data_version)

    if team_name:
        query = query.filter(Player.team_name == team_name)

    sort_columns = {
        "flowers": [desc(PlayerReactionSummary.flowers), desc(total_reactions), desc(PlayerReactionSummary.updated_at), attribute_model.uid.asc()],
        "eggs": [desc(PlayerReactionSummary.eggs), desc(total_reactions), desc(PlayerReactionSummary.updated_at), attribute_model.uid.asc()],
        "net": [desc(net_score), desc(PlayerReactionSummary.flowers), PlayerReactionSummary.eggs.asc(), desc(PlayerReactionSummary.updated_at), attribute_model.uid.asc()],
    }
    return query.order_by(*sort_columns.get(metric, sort_columns["flowers"])).limit(limit).all()
