"""data feedback reports

Revision ID: 20260327_000014
Revises: 20260318_000013
Create Date: 2026-03-27 03:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260327_000014"
down_revision: Union[str, Sequence[str], None] = "20260318_000013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("data_feedback_reports"):
        return

    op.create_table(
        "data_feedback_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_uid", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=True),
        sa.Column("issue_type", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("suggested_correction", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(), nullable=True),
        sa.Column("source_page", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'open'")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_feedback_reports_id", "data_feedback_reports", ["id"], unique=False)
    op.create_index("ix_data_feedback_reports_player_uid", "data_feedback_reports", ["player_uid"], unique=False)
    op.create_index("ix_data_feedback_reports_player_name", "data_feedback_reports", ["player_name"], unique=False)
    op.create_index("ix_data_feedback_reports_issue_type", "data_feedback_reports", ["issue_type"], unique=False)
    op.create_index("ix_data_feedback_reports_status", "data_feedback_reports", ["status"], unique=False)
    op.create_index("ix_data_feedback_reports_created_at", "data_feedback_reports", ["created_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for data feedback reports.")
