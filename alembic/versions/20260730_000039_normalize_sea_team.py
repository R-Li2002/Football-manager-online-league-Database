"""normalize the hidden sea team and out-of-league players

Revision ID: 20260730_000039
Revises: 20260730_000038
Create Date: 2026-07-30 21:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000039"
down_revision: Union[str, Sequence[str], None] = "20260730_000038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_SEA_NAME = "85大海"
SEA_NAME = "大海"
LEAGUE_LEVELS = ("超级", "甲级", "乙级")

TEAM_ID_COLUMNS = (
    ("players", "team_id"),
    ("matches", "home_team_id"),
    ("matches", "away_team_id"),
    ("match_player_events", "team_id"),
    ("cup_matches", "home_team_id"),
    ("cup_matches", "away_team_id"),
    ("cup_matches", "winner_team_id"),
    ("player_competition_stats", "team_id"),
    ("player_suspension_records", "team_id"),
    ("coaches", "team_id"),
    ("team_lineups", "team_id"),
    ("transfer_logs", "from_team_id"),
    ("transfer_logs", "to_team_id"),
)

TEAM_NAME_COLUMNS = (
    ("players", "team_name"),
    ("matches", "home_team_name"),
    ("matches", "away_team_name"),
    ("match_player_events", "team_name"),
    ("cup_matches", "home_team_name"),
    ("cup_matches", "away_team_name"),
    ("cup_matches", "winner_team_name"),
    ("player_competition_stats", "team_name"),
    ("player_suspension_records", "team_name"),
    ("coaches", "team_name"),
    ("transfer_logs", "from_team"),
    ("transfer_logs", "to_team"),
)


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return inspector.has_table(table_name) and column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    old_id = bind.execute(
        sa.text("SELECT id FROM teams WHERE name = :name"), {"name": OLD_SEA_NAME}
    ).scalar()
    sea_id = bind.execute(
        sa.text("SELECT id FROM teams WHERE name = :name"), {"name": SEA_NAME}
    ).scalar()

    if old_id is not None and sea_id is None:
        bind.execute(
            sa.text("UPDATE teams SET name = :new_name WHERE id = :team_id"),
            {"new_name": SEA_NAME, "team_id": old_id},
        )
        sea_id = old_id
    elif old_id is not None and sea_id is not None and old_id != sea_id:
        for table_name, column_name in TEAM_ID_COLUMNS:
            if _has_column(inspector, table_name, column_name):
                bind.execute(
                    sa.text(f'UPDATE "{table_name}" SET "{column_name}" = :sea_id WHERE "{column_name}" = :old_id'),
                    {"sea_id": sea_id, "old_id": old_id},
                )
        bind.execute(sa.text("DELETE FROM teams WHERE id = :old_id"), {"old_id": old_id})

    player_count = 0
    if inspector.has_table("players"):
        player_count = bind.execute(sa.text("SELECT COUNT(*) FROM players")).scalar() or 0

    if sea_id is None and player_count:
        bind.execute(
            sa.text(
                "INSERT INTO teams (name, manager, level, wage) "
                "VALUES (:name, '系统', '隐藏', 0.0)"
            ),
            {"name": SEA_NAME},
        )
        sea_id = bind.execute(
            sa.text("SELECT id FROM teams WHERE name = :name"), {"name": SEA_NAME}
        ).scalar_one()

    for table_name, column_name in TEAM_NAME_COLUMNS:
        if _has_column(inspector, table_name, column_name):
            bind.execute(
                sa.text(f'UPDATE "{table_name}" SET "{column_name}" = :new_name WHERE "{column_name}" = :old_name'),
                {"new_name": SEA_NAME, "old_name": OLD_SEA_NAME},
            )

    if inspector.has_table("players") and sea_id is not None:
        bind.execute(
            sa.text(
                """
                UPDATE players
                SET team_id = :sea_id, team_name = :sea_name
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM teams
                    WHERE teams.level IN ('超级', '甲级', '乙级')
                      AND (teams.id = players.team_id OR teams.name = players.team_name)
                )
                """
            ),
            {"sea_id": sea_id, "sea_name": SEA_NAME},
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for sea-team normalization.")
