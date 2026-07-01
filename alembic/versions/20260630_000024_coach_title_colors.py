"""coach title colors

Revision ID: 20260630_000024
Revises: 20260630_000023
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_000024"
down_revision: Union[str, Sequence[str], None] = "20260630_000023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("coaches"):
        columns = {column["name"] for column in inspector.get_columns("coaches")}
        if "title_color" not in columns:
            op.add_column("coaches", sa.Column("title_color", sa.String(), nullable=True, server_default="white"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coach title colors.")
