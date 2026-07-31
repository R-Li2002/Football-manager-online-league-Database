from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models import Player, Team
from repositories.team_repository import get_team_by_name
from search_normalization import build_search_normalized_keys

LEAGUE_LEVELS = ("超级", "甲级", "乙级")


def league_player_membership_filter():
    league_team_ids = select(Team.id).where(Team.level.in_(LEAGUE_LEVELS))
    league_team_names = select(Team.name).where(Team.level.in_(LEAGUE_LEVELS))
    return or_(
        and_(Player.team_id.is_not(None), Player.team_id.in_(league_team_ids)),
        and_(Player.team_name.is_not(None), Player.team_name.in_(league_team_names)),
    )


def get_player_by_uid(db: Session, uid: int) -> Player | None:
    return db.query(Player).filter(Player.uid == uid).first()


def list_all_players(db: Session) -> list[Player]:
    return db.query(Player).all()


def list_league_players(db: Session) -> list[Player]:
    return db.query(Player).filter(league_player_membership_filter()).order_by(Player.team_name, Player.name).all()


def count_league_players(db: Session) -> int:
    return db.query(Player).filter(league_player_membership_filter()).count()


def list_sea_players(db: Session) -> list[Player]:
    return db.query(Player).filter(~league_player_membership_filter()).order_by(Player.name).all()


def player_is_in_league(db: Session, player: Player) -> bool:
    return db.query(Player.uid).filter(Player.uid == player.uid, league_player_membership_filter()).first() is not None


def list_players_excluding_team(db: Session, excluded_team_name: str | None = None) -> list[Player]:
    query = db.query(Player)
    if excluded_team_name:
        query = query.filter(Player.team_name != excluded_team_name)
    return query.order_by(Player.team_name, Player.name).all()


def count_players_excluding_team(db: Session, excluded_team_name: str | None = None) -> int:
    query = db.query(Player)
    if excluded_team_name:
        query = query.filter(Player.team_name != excluded_team_name)
    return query.count()


def search_players_by_name(db: Session, player_name: str) -> list[Player]:
    strict_keys, loose_keys = build_search_normalized_keys(player_name)
    query = db.query(Player)
    filters = []
    for key in strict_keys:
        filters.append(func.heigo_normalize(Player.name).contains(key))
    for key in loose_keys:
        filters.append(func.heigo_normalize_loose(Player.name).contains(key))
    if filters:
        return query.filter(or_(*filters)).all()
    return query.filter(Player.name.ilike(f"%{player_name}%")).all()


def map_player_uid_to_team_name(db: Session) -> dict[int, str]:
    league_players = {
        uid: team_name
        for uid, team_name in db.query(Player.uid, Player.team_name).filter(league_player_membership_filter()).all()
    }
    return {
        uid: league_players.get(uid, "大海")
        for (uid,) in db.query(Player.uid).all()
    }


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
