"""player habit raw/high code fields

Revision ID: 20260318_000013
Revises: 20260318_000012
Create Date: 2026-03-18 18:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260318_000013"
down_revision: Union[str, Sequence[str], None] = "20260318_000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return
    op.add_column(table_name, sa.Column(column_name, sa.String(), nullable=True))


def upgrade() -> None:
    for table_name in ("player_attributes", "player_attribute_versions"):
        _add_column_if_missing(table_name, "player_habits_raw_code")
        _add_column_if_missing(table_name, "player_habits_high_bits")


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player habit code fields.")
