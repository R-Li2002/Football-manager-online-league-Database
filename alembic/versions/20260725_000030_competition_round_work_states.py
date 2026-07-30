"""competition round work states

Revision ID: 20260725_000030
Revises: 20260717_000029
Create Date: 2026-07-25 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_000030"
down_revision: Union[str, Sequence[str], None] = "20260717_000029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("competition_round_work_states"):
        return

    op.create_table(
        "competition_round_work_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("round_start", sa.Integer(), nullable=False),
        sa.Column("round_end", sa.Integer(), nullable=False),
        sa.Column("suspension_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("suspension_confirmed_by", sa.String(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_by", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level", "round_start", name="uq_competition_round_work_level_start"),
    )
    op.create_index("ix_competition_round_work_states_level", "competition_round_work_states", ["level"])
    op.create_index("ix_competition_round_work_states_round_start", "competition_round_work_states", ["round_start"])
    op.create_index("ix_competition_round_work_states_suspension_confirmed_by", "competition_round_work_states", ["suspension_confirmed_by"])
    op.create_index("ix_competition_round_work_states_completed_by", "competition_round_work_states", ["completed_by"])


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for competition round work states.")
