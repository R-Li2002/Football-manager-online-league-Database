"""match player events

Revision ID: 20260702_000026
Revises: 20260630_000025
Create Date: 2026-07-02 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_000026"
down_revision: Union[str, Sequence[str], None] = "20260630_000025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("match_player_events"):
        return

    op.create_table(
        "match_player_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("player_uid", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_uid"], ["players.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_player_events_id", "match_player_events", ["id"], unique=False)
    op.create_index("ix_match_player_events_match_id", "match_player_events", ["match_id"], unique=False)
    op.create_index("ix_match_player_events_team_id", "match_player_events", ["team_id"], unique=False)
    op.create_index("ix_match_player_events_team_name", "match_player_events", ["team_name"], unique=False)
    op.create_index("ix_match_player_events_player_uid", "match_player_events", ["player_uid"], unique=False)
    op.create_index("ix_match_player_events_player_name", "match_player_events", ["player_name"], unique=False)
    op.create_index("ix_match_player_events_event_type", "match_player_events", ["event_type"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for match player events.")
