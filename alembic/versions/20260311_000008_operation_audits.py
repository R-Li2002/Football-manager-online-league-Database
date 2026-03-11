"""operation audits

Revision ID: 20260311_000008
Revises: 20260311_000007
Create Date: 2026-03-11 14:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260311_000008"
down_revision: Union[str, Sequence[str], None] = "20260311_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("operation_audits"):
        return

    op.create_table(
        "operation_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operation_audits_id", "operation_audits", ["id"], unique=False)
    op.create_index("ix_operation_audits_category", "operation_audits", ["category"], unique=False)
    op.create_index("ix_operation_audits_action", "operation_audits", ["action"], unique=False)
    op.create_index("ix_operation_audits_status", "operation_audits", ["status"], unique=False)
    op.create_index("ix_operation_audits_source", "operation_audits", ["source"], unique=False)
    op.create_index("ix_operation_audits_operator", "operation_audits", ["operator"], unique=False)
    op.create_index("ix_operation_audits_created_at", "operation_audits", ["created_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for operation audits.")
