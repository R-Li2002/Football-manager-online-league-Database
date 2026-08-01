"""cup standings work permission

Revision ID: 20260801_000042
Revises: 20260731_000041
Create Date: 2026-08-01 23:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_000042"
down_revision: Union[str, Sequence[str], None] = "20260731_000041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("coach_accounts"):
        return
    columns = {column["name"] for column in inspector.get_columns("coach_accounts")}
    if "can_manage_cup_standings" not in columns:
        op.add_column(
            "coach_accounts",
            sa.Column("can_manage_cup_standings", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for cup standings permission.")
