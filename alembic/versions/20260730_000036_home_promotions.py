"""configurable home promotions

Revision ID: 20260730_000036
Revises: 20260730_000035
Create Date: 2026-07-30 10:45:00
"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000036"
down_revision: Union[str, Sequence[str], None] = "20260730_000035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("home_promotions"):
        op.create_table(
            "home_promotions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=False, server_default="announcement"),
            sa.Column("theme", sa.String(), nullable=False, server_default="violet"),
            sa.Column("icon", sa.String(), nullable=False, server_default="megaphone"),
            sa.Column("eyebrow", sa.String(), nullable=False, server_default="HEIGO Broadcast"),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("image_url", sa.String(), nullable=True),
            sa.Column("action_label", sa.String(), nullable=True),
            sa.Column("action_kind", sa.String(), nullable=False, server_default="none"),
            sa.Column("action_target", sa.String(), nullable=True),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_pinned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_dismissible", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("ends_at", sa.DateTime(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=False, server_default="custom"),
            sa.Column("source_key", sa.String(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_type", "source_key", name="uq_home_promotions_source"),
        )
        for column in ("content_type", "is_active", "is_pinned", "sort_order", "starts_at", "ends_at", "source_type", "source_key", "created_at", "updated_at"):
            op.create_index(f"ix_home_promotions_{column}", "home_promotions", [column], unique=False)

    existing = bind.execute(sa.text("SELECT COUNT(*) FROM home_promotions")).scalar() or 0
    if existing:
        return
    now = datetime.now()
    bind.execute(
        sa.text(
            """
            INSERT INTO home_promotions (
                content_type, theme, icon, eyebrow, title, body, action_label,
                action_kind, action_target, is_active, is_pinned, is_dismissible,
                sort_order, source_type, source_key, created_by, updated_by, created_at, updated_at
            ) VALUES (
                'announcement', 'blue', 'list', 'CANDIDATE LISTS',
                '87届初期强制名单已发布',
                '教练可进入球员库的候选名单范围，并继续按位置、能力和俱乐部筛选球员。',
                '查看名单', 'tab', 'database:candidates', 1, 0, 1, 80,
                'legacy', 'candidate-lists-87', 'system', 'system', :now, :now
            )
            """
        ),
        {"now": now},
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for home promotions.")
