"""structured data status round markers

Revision ID: 20260730_000038
Revises: 20260730_000037
Create Date: 2026-07-30 20:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000038"
down_revision: Union[str, Sequence[str], None] = "20260730_000037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("site_notes")}
    if "round_no" not in columns:
        op.add_column("site_notes", sa.Column("round_no", sa.Integer(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for data status round markers.")
