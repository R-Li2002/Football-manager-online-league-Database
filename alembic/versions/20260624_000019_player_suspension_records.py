"""player suspension records

Revision ID: 20260624_000019
Revises: 20260623_000018
Create Date: 2026-06-24 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_000019"
down_revision: Union[str, Sequence[str], None] = "20260623_000018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("player_suspension_records"):
        return

    op.create_table(
        "player_suspension_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_uid", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("yellow_cards", sa.Integer(), nullable=True),
        sa.Column("red_card_suspended", sa.Integer(), nullable=True),
        sa.Column("red_injury_suspended", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["player_uid"], ["players.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_uid", name="uq_player_suspension_records_player_uid"),
    )
    op.create_index("ix_player_suspension_records_id", "player_suspension_records", ["id"], unique=False)
    op.create_index("ix_player_suspension_records_player_uid", "player_suspension_records", ["player_uid"], unique=False)
    op.create_index("ix_player_suspension_records_player_name", "player_suspension_records", ["player_name"], unique=False)
    op.create_index("ix_player_suspension_records_team_id", "player_suspension_records", ["team_id"], unique=False)
    op.create_index("ix_player_suspension_records_team_name", "player_suspension_records", ["team_name"], unique=False)
    op.create_index("ix_player_suspension_records_level", "player_suspension_records", ["level"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player suspension records.")
