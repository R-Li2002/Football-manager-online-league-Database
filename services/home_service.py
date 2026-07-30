from sqlalchemy.orm import Session

from repositories.attribute_repository import count_attribute_players, get_default_attribute_version
from repositories.player_repository import count_players_excluding_team
from repositories.team_repository import count_visible_teams

VISIBLE_LEVEL = "隐藏"
SEA_TEAM_NAME = "85大海"


def get_home_summary(db: Session) -> dict[str, int | str]:
    default_attribute_version = get_default_attribute_version(db)
    return {
        "team_count": count_visible_teams(db, VISIBLE_LEVEL),
        "player_count": count_players_excluding_team(db, SEA_TEAM_NAME),
        "database_player_count": count_attribute_players(db, default_attribute_version),
        "default_attribute_version": default_attribute_version,
    }
