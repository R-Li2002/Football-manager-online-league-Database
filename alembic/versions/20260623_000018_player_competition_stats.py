"""player competition stats

Revision ID: 20260623_000018
Revises: 20260623_000017
Create Date: 2026-06-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260623_000018"
down_revision: Union[str, Sequence[str], None] = "20260623_000017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("player_competition_stats"):
        return

    op.create_table(
        "player_competition_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_uid", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["player_uid"], ["players.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_competition_stats_id", "player_competition_stats", ["id"], unique=False)
    op.create_index("ix_player_competition_stats_player_uid", "player_competition_stats", ["player_uid"], unique=False)
    op.create_index("ix_player_competition_stats_player_name", "player_competition_stats", ["player_name"], unique=False)
    op.create_index("ix_player_competition_stats_team_id", "player_competition_stats", ["team_id"], unique=False)
    op.create_index("ix_player_competition_stats_team_name", "player_competition_stats", ["team_name"], unique=False)
    op.create_index("ix_player_competition_stats_level", "player_competition_stats", ["level"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player competition stats.")
