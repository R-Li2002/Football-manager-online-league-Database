"""cup knockout matches

Revision ID: 20260623_000017
Revises: 20260622_000016
Create Date: 2026-06-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260623_000017"
down_revision: Union[str, Sequence[str], None] = "20260622_000016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("cup_matches"):
        return

    op.create_table(
        "cup_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("slot_no", sa.Integer(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=True),
        sa.Column("home_team_name", sa.String(), nullable=True),
        sa.Column("away_team_id", sa.Integer(), nullable=True),
        sa.Column("away_team_name", sa.String(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("winner_team_id", sa.Integer(), nullable=True),
        sa.Column("winner_team_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition", "stage", "slot_no", name="uq_cup_matches_competition_stage_slot"),
    )
    op.create_index("ix_cup_matches_id", "cup_matches", ["id"], unique=False)
    op.create_index("ix_cup_matches_competition", "cup_matches", ["competition"], unique=False)
    op.create_index("ix_cup_matches_stage", "cup_matches", ["stage"], unique=False)
    op.create_index("ix_cup_matches_slot_no", "cup_matches", ["slot_no"], unique=False)
    op.create_index("ix_cup_matches_home_team_id", "cup_matches", ["home_team_id"], unique=False)
    op.create_index("ix_cup_matches_away_team_id", "cup_matches", ["away_team_id"], unique=False)
    op.create_index("ix_cup_matches_winner_team_id", "cup_matches", ["winner_team_id"], unique=False)
    op.create_index("ix_cup_matches_status", "cup_matches", ["status"], unique=False)
def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for cup matches.")
