from sqlalchemy.orm import Session

from models import Player, Team
from repositories.team_repository import get_team_by_name

SEA_TEAM_NAME = "85\u5927\u6d77"


def get_sea_team(db: Session) -> Team | None:
    return get_team_by_name(db, SEA_TEAM_NAME)


def assign_player_team(player: Player, team: Team) -> None:
    player.team_id = team.id
    player.team_name = team.name


def assign_player_team_by_name(db: Session, player: Player, team_name: str) -> None:
    team = get_team_by_name(db, team_name)
    if team:
        assign_player_team(player, team)
    else:
        player.team_id = None
        player.team_name = team_name
