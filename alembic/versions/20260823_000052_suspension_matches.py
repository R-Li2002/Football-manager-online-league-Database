"""add editable suspension match count

Revision ID: 20260823_000052
Revises: 20260821_000051
Create Date: 2026-08-23 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_000052"
down_revision: Union[str, Sequence[str], None] = "20260821_000051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("player_suspension_records"):
        return
    columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
    if "suspension_matches" not in columns:
        op.add_column(
            "player_suspension_records",
            sa.Column("suspension_matches", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("player_suspension_records"):
        return
    columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
    if "suspension_matches" in columns:
        op.drop_column("player_suspension_records", "suspension_matches")
