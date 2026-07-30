"""team-specific wage cap override

Revision ID: 20260730_000035
Revises: 20260729_000034
Create Date: 2026-07-30 09:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000035"
down_revision: Union[str, Sequence[str], None] = "20260729_000034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("teams"):
        return
    columns = {column["name"] for column in inspector.get_columns("teams")}
    if "wage_cap" not in columns:
        op.add_column("teams", sa.Column("wage_cap", sa.Float(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for team wage caps.")
