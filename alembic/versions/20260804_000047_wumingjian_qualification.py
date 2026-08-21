"""add wumingjian cup qualification snapshot

Revision ID: 20260804_000047
Revises: 20260804_000046
Create Date: 2026-08-04 02:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_000047"
down_revision: Union[str, Sequence[str], None] = "20260804_000046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("wumingjian_qualification_teams"):
        return
    op.create_table(
        "wumingjian_qualification_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("manager", sa.String(), nullable=True),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("source_rank", sa.Integer(), nullable=False),
        sa.Column("qualification_type", sa.String(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", name="uq_wumingjian_qualification_team"),
    )
    op.create_index(op.f("ix_wumingjian_qualification_teams_id"), "wumingjian_qualification_teams", ["id"], unique=False)
    op.create_index(op.f("ix_wumingjian_qualification_teams_team_id"), "wumingjian_qualification_teams", ["team_id"], unique=False)
    op.create_index(op.f("ix_wumingjian_qualification_teams_level"), "wumingjian_qualification_teams", ["level"], unique=False)
    op.create_index(op.f("ix_wumingjian_qualification_teams_qualification_type"), "wumingjian_qualification_teams", ["qualification_type"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the Wumingjian qualification snapshot.")
