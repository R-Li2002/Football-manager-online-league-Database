"""home promotion modal delivery

Revision ID: 20260730_000037
Revises: 20260730_000036
Create Date: 2026-07-30 13:10:00
"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000037"
down_revision: Union[str, Sequence[str], None] = "20260730_000036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("home_promotions")}
    if "display_mode" not in columns:
        op.add_column(
            "home_promotions",
            sa.Column("display_mode", sa.String(), nullable=False, server_default="board"),
        )

    existing = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM home_promotions "
            "WHERE source_type = 'site_intro' AND source_key = 'coach-welcome'"
        )
    ).scalar() or 0
    if existing:
        return

    now = datetime.now()
    bind.execute(
        sa.text(
            """
            INSERT INTO home_promotions (
                content_type, theme, icon, eyebrow, title, body, action_label,
                action_kind, action_target, display_mode, is_active, is_pinned,
                is_dismissible, sort_order, source_type, source_key, created_by,
                updated_by, created_at, updated_at
            ) VALUES (
                'announcement', 'violet', 'star', 'WELCOME TO HEIGO',
                '为联机联赛教练准备的一站式数据台',
                :body,
                '进入球队中心', 'tab', 'team', 'modal', 1, 1, 1, 10,
                'site_intro', 'coach-welcome', 'system', 'system', :now, :now
            )
            """
        ),
        {
            "body": (
                "球队中心｜集中查看赛程、伤停、联赛名单、战术板、战力分析和球员挂牌信息，并支持一键复制。\n"
                "联赛数据｜积分榜、赛程、球员数据榜单与伤停信息随时便捷查看。\n"
                "10W+ 球员库｜支持大海状态、位置与各项属性的自定义高级搜索，并提供多类球员名单参考。\n"
                "教练主页｜自由填写自我介绍、个性装点主页并陈列荣誉，留下自己的联赛名片。"
            ),
            "now": now,
        },
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for home promotion modal delivery.")
