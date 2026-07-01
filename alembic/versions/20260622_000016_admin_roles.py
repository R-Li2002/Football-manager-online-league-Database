"""admin user roles

Revision ID: 20260622_000016
Revises: 20260622_000015
Create Date: 2026-06-22 01:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_000016"
down_revision: Union[str, Sequence[str], None] = "20260622_000015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("admin_users"):
        return

    columns = {column["name"] for column in inspector.get_columns("admin_users")}
    if "role" not in columns:
        op.add_column("admin_users", sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'admin'")))
        op.create_index("ix_admin_users_role", "admin_users", ["role"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for admin roles.")
