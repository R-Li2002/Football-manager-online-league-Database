"""team lineup previews

Revision ID: 20260728_000033
Revises: 20260726_000032
Create Date: 2026-07-28 18:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_000033"
down_revision: Union[str, Sequence[str], None] = "20260726_000032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("team_lineups"):
        return
    op.create_table(
        "team_lineups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("formation", sa.String(), nullable=False, server_default="4-3-3"),
        sa.Column("picks_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", name="uq_team_lineups_team_id"),
    )
    op.create_index("ix_team_lineups_team_id", "team_lineups", ["team_id"], unique=True)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for team lineups.")
