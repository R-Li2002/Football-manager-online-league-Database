"""coach assistants

Revision ID: 20260630_000025
Revises: 20260630_000024
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_000025"
down_revision: Union[str, Sequence[str], None] = "20260630_000024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("coach_assistants"):
        op.create_table(
            "coach_assistants",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("coach_uid", sa.String(), sa.ForeignKey("coaches.uid", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("level", sa.String(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_coach_assistants_id", "coach_assistants", ["id"], unique=False)
        op.create_index("ix_coach_assistants_coach_uid", "coach_assistants", ["coach_uid"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coach assistants.")
