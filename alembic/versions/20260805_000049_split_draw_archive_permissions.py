"""split draw and season archive permissions

Revision ID: 20260805_000049
Revises: 20260805_000048
Create Date: 2026-08-05 12:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_000049"
down_revision: Union[str, Sequence[str], None] = "20260805_000048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("coach_accounts")}
    if "can_manage_archives" not in columns:
        with op.batch_alter_table("coach_accounts") as batch_op:
            batch_op.add_column(sa.Column("can_manage_archives", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("coach_accounts")}
    if "can_manage_archives" in columns:
        with op.batch_alter_table("coach_accounts") as batch_op:
            batch_op.drop_column("can_manage_archives")
