"""daily report work permission

Revision ID: 20260804_000046
Revises: 20260803_000045
Create Date: 2026-08-04 00:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_000046"
down_revision: Union[str, Sequence[str], None] = "20260803_000045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("coach_accounts"):
        return
    columns = {column["name"] for column in inspector.get_columns("coach_accounts")}
    if "can_manage_daily_reports" not in columns:
        op.add_column(
            "coach_accounts",
            sa.Column("can_manage_daily_reports", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for daily report permission.")
