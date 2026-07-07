"""coach work permissions

Revision ID: 20260703_000028
Revises: 20260702_000027
Create Date: 2026-07-03 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260703_000028"
down_revision: Union[str, Sequence[str], None] = "20260702_000027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _columns(inspector, "coach_accounts")
    if not columns:
        return

    for column_name in (
        "can_manage_schedule",
        "can_manage_suspensions",
        "can_manage_candidate_lists",
    ):
        if column_name not in columns:
            op.add_column(
                "coach_accounts",
                sa.Column(column_name, sa.Integer(), nullable=False, server_default=sa.text("0")),
            )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coach work permissions.")
