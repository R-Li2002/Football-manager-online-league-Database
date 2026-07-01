"""team logo uploads

Revision ID: 20260630_000023
Revises: 20260630_000022
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_000023"
down_revision: Union[str, Sequence[str], None] = "20260630_000022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("teams"):
        columns = {column["name"] for column in inspector.get_columns("teams")}
        if "logo_path" not in columns:
            op.add_column("teams", sa.Column("logo_path", sa.String(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for team logos.")
