"""coach QQ login and first password change

Revision ID: 20260729_000034
Revises: 20260728_000033
Create Date: 2026-07-29 12:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_000034"
down_revision: Union[str, Sequence[str], None] = "20260728_000033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _columns(inspector, "coach_accounts")
    if not columns:
        return
    if "qq_number" not in columns:
        op.add_column("coach_accounts", sa.Column("qq_number", sa.String(), nullable=True))
    if "must_change_password" not in columns:
        op.add_column(
            "coach_accounts",
            sa.Column("must_change_password", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )
    inspector = sa.inspect(bind)
    indexes = _indexes(inspector, "coach_accounts")
    if "ix_coach_accounts_qq_number" not in indexes:
        op.create_index("ix_coach_accounts_qq_number", "coach_accounts", ["qq_number"], unique=True)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coach QQ login.")
