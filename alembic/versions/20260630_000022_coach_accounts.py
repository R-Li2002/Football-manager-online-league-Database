"""coach accounts and standardized honors

Revision ID: 20260630_000022
Revises: 20260630_000021
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_000022"
down_revision: Union[str, Sequence[str], None] = "20260630_000021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    honor_columns = _columns(inspector, "coach_honors")
    if "coach_honors" in inspector.get_table_names():
        if "edition" not in honor_columns:
            op.add_column("coach_honors", sa.Column("edition", sa.Integer(), nullable=True))
        if "placement" not in honor_columns:
            op.add_column("coach_honors", sa.Column("placement", sa.String(), nullable=True))

    if not inspector.has_table("coach_accounts"):
        op.create_table(
            "coach_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("coach_uid", sa.String(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["coach_uid"], ["coaches.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("coach_uid", name="uq_coach_accounts_coach_uid"),
            sa.UniqueConstraint("username", name="uq_coach_accounts_username"),
        )
        op.create_index("ix_coach_accounts_id", "coach_accounts", ["id"], unique=False)
        op.create_index("ix_coach_accounts_coach_uid", "coach_accounts", ["coach_uid"], unique=False)
        op.create_index("ix_coach_accounts_username", "coach_accounts", ["username"], unique=False)

    if not inspector.has_table("coach_sessions"):
        op.create_table(
            "coach_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("coach_uid", sa.String(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["coach_uid"], ["coaches.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token", name="uq_coach_sessions_token"),
        )
        op.create_index("ix_coach_sessions_id", "coach_sessions", ["id"], unique=False)
        op.create_index("ix_coach_sessions_token", "coach_sessions", ["token"], unique=False)
        op.create_index("ix_coach_sessions_coach_uid", "coach_sessions", ["coach_uid"], unique=False)
        op.create_index("ix_coach_sessions_username", "coach_sessions", ["username"], unique=False)
        op.create_index("ix_coach_sessions_expires_at", "coach_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coach accounts.")
