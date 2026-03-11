from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models import Player, Team
from repositories.team_repository import get_team_by_name


def get_player_by_uid(db: Session, uid: int) -> Player | None:
    return db.query(Player).filter(Player.uid == uid).first()


def list_all_players(db: Session) -> list[Player]:
    return db.query(Player).all()


def list_players_excluding_team(db: Session, excluded_team_name: str | None = None) -> list[Player]:
    query = db.query(Player)
    if excluded_team_name:
        query = query.filter(Player.team_name != excluded_team_name)
    return query.order_by(Player.team_name, Player.name).all()


def search_players_by_name(db: Session, player_name: str) -> list[Player]:
    return db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).all()


def map_player_uid_to_team_name(db: Session) -> dict[int, str]:
    return {uid: team_name for uid, team_name in db.query(Player.uid, Player.team_name).all()}


def team_player_filter(team: Team):
    return or_(
        Player.team_id == team.id,
        and_(Player.team_id.is_(None), Player.team_name == team.name),
    )


def get_team_players(db: Session, team: Team) -> list[Player]:
    return db.query(Player).filter(team_player_filter(team)).all()


def get_players_by_team_name(db: Session, team_name: str) -> list[Player]:
    team = get_team_by_name(db, team_name)
    if not team:
        return db.query(Player).filter(Player.team_name == team_name).order_by(Player.name).all()
    return db.query(Player).filter(team_player_filter(team)).order_by(Player.name).all()


def load_players_grouped_by_teams(db: Session, teams: list[Team]) -> dict[int, list[Player]]:
    if not teams:
        return {}

    team_ids = {team.id for team in teams}
    team_name_to_id = {team.name: team.id for team in teams}
    players = (
        db.query(Player)
        .filter(
            or_(
                Player.team_id.in_(team_ids),
                and_(Player.team_id.is_(None), Player.team_name.in_(team_name_to_id)),
            )
        )
        .all()
    )

    players_by_team_id = {team.id: [] for team in teams}
    for player in players:
        target_team_id = player.team_id if player.team_id in team_ids else team_name_to_id.get(player.team_name)
        if target_team_id in players_by_team_id:
            players_by_team_id[target_team_id].append(player)
    return players_by_team_id
