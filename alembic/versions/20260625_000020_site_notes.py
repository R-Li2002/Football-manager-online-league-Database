"""site notes

Revision ID: 20260625_000020
Revises: 20260624_000019
Create Date: 2026-06-25 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260625_000020"
down_revision: Union[str, Sequence[str], None] = "20260624_000019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("site_notes"):
        return

    op.create_table(
        "site_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_site_notes_key"),
    )
    op.create_index("ix_site_notes_key", "site_notes", ["key"], unique=True)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for site notes.")
