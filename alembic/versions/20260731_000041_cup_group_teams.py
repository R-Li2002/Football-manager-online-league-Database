"""add cup group team assignments

Revision ID: 20260731_000041
Revises: 20260730_000040
Create Date: 2026-07-31 22:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_000041"
down_revision: Union[str, Sequence[str], None] = "20260730_000040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("cup_group_teams"):
        return
    op.create_table(
        "cup_group_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition", sa.String(), nullable=False),
        sa.Column("group_no", sa.Integer(), nullable=False),
        sa.Column("slot_no", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition", "group_no", "slot_no", name="uq_cup_group_teams_competition_group_slot"),
        sa.UniqueConstraint("competition", "team_id", name="uq_cup_group_teams_competition_team"),
    )
    op.create_index(op.f("ix_cup_group_teams_id"), "cup_group_teams", ["id"], unique=False)
    op.create_index(op.f("ix_cup_group_teams_competition"), "cup_group_teams", ["competition"], unique=False)
    op.create_index(op.f("ix_cup_group_teams_group_no"), "cup_group_teams", ["group_no"], unique=False)
    op.create_index(op.f("ix_cup_group_teams_slot_no"), "cup_group_teams", ["slot_no"], unique=False)
    op.create_index(op.f("ix_cup_group_teams_team_id"), "cup_group_teams", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cup_group_teams_team_id"), table_name="cup_group_teams")
    op.drop_index(op.f("ix_cup_group_teams_slot_no"), table_name="cup_group_teams")
    op.drop_index(op.f("ix_cup_group_teams_group_no"), table_name="cup_group_teams")
    op.drop_index(op.f("ix_cup_group_teams_competition"), table_name="cup_group_teams")
    op.drop_index(op.f("ix_cup_group_teams_id"), table_name="cup_group_teams")
    op.drop_table("cup_group_teams")
