"""site visit stats

Revision ID: 20260717_000029
Revises: 20260703_000028
Create Date: 2026-07-17 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_000029"
down_revision: Union[str, Sequence[str], None] = "20260703_000028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("site_visit_stats"):
        return

    op.create_table(
        "site_visit_stats",
        sa.Column("visit_date", sa.String(length=10), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("visit_date"),
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for site visit stats.")
