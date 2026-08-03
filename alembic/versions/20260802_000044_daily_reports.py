"""daily reports and narrative templates

Revision ID: 20260802_000044
Revises: 20260802_000043
Create Date: 2026-08-02 21:10:00
"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260802_000044"
down_revision: Union[str, Sequence[str], None] = "20260802_000043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_TEMPLATES = (
    ("narrow_win", "一球险胜", "{winner} {score} 险胜 {loser}，一球之差拿下关键胜利。", 10),
    ("narrow_win", "鏖战过关", "{winner} {score} 力克 {loser}，胶着较量最终分出胜负。", 20),
    ("regular_win", "效率制胜", "{winner} {score} 击败 {loser}，进攻效率更胜一筹。", 10),
    ("regular_win", "稳稳拿下", "{winner} 以 {score} 战胜 {loser}，把场面优势转化为结果。", 20),
    ("big_win", "火力全开", "{winner} {score} 大胜 {loser}，进攻火力全面释放。", 10),
    ("big_win", "强势横扫", "{winner} 以 {score} 强势击败 {loser}，整场比赛几乎没有给对手留下喘息空间。", 20),
    ("clean_sheet_rout", "零封完胜", "{winner} {score} 完胜 {loser}，以一场强势零封收下胜利。", 10),
    ("clean_sheet_rout", "攻守压制", "{winner} 以 {score} 横扫 {loser}，攻防两端都占据明显上风。", 20),
    ("high_scoring_win", "进球大战", "{winner} {score} 力克 {loser}，双方联手轰入 {total_goals} 球，上演疯狂对攻。", 10),
    ("high_scoring_win", "火力对轰", "{winner} 在进球大战中以 {score} 击败 {loser}，两队把比赛变成一场火力对轰。", 20),
    ("goalless_draw", "互交白卷", "{home_team} 与 {away_team} 互交白卷，双方在谨慎拉扯中各取一分。", 10),
    ("goalless_draw", "闷平收场", "{home_team} 0:0 战平 {away_team}，两队始终未能敲开对方球门。", 20),
    ("draw", "握手言和", "{home_team} {score} 战平 {away_team}，鏖战过后握手言和。", 10),
    ("draw", "难分高下", "{home_team} 与 {away_team} 最终战成 {score}，双方难分高下。", 20),
    ("high_scoring_draw", "对攻平局", "{home_team} 与 {away_team} 大打对攻，最终 {score} 难分高下。", 10),
    ("high_scoring_draw", "进球盛宴", "{home_team} {score} 战平 {away_team}，{total_goals} 球盛宴过后仍未分出胜负。", 20),
    ("forfeit", "判负说明", "{winner} 因比赛判定取得本场结果，最终比分为 {score}。", 10),
    ("double_forfeit", "双方判负说明", "{home_team} 与 {away_team} 本场均被判负，比赛按 {score} 记录。", 10),
    ("winning_hattrick", "帽子戏法领胜", "{player} 独中三元，成为 {team} 取胜的头号功臣。", 10),
    ("winning_hattrick", "三球主角", "{player} 上演帽子戏法，用三粒进球主导胜局。", 20),
    ("losing_hattrick", "帽子戏法难救主", "{player} 帽子戏法仍难救主，个人高光未能为 {team} 换来胜利。", 10),
    ("losing_hattrick", "三球空砍", "{player} 独中三元却遗憾成为空砍，{team} 最终仍败下阵来。", 20),
    ("hattrick", "平局三球", "{player} 上演帽子戏法，成为这场对攻战最耀眼的球员。", 10),
    ("brace", "梅开二度", "{player} 梅开二度，成为 {team} 进攻端最醒目的名字。", 10),
    ("playmaker", "助攻核心", "{player} 送出 {assists} 次助攻，成为 {team} 的进攻枢纽。", 10),
    ("goal_and_assist", "传射建功", "{player} 贡献 {goals} 球 {assists} 助攻，在攻门与串联两端都有亮眼表现。", 10),
    ("mvp", "最佳球员", "{player} 当选本场最佳，成为这场比赛最受认可的球员。", 10),
    ("power_upset", "战力反差", "赛前阵容战力处于下风的 {winner} 打出更高效率，击败了 {loser}。", 10),
    ("power_close", "旗鼓相当", "两队阵容战力十分接近，这场比赛也呈现出势均力敌的走势。", 10),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("daily_report_narrative_templates"):
        op.create_table(
            "daily_report_narrative_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("template_text", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
            sa.Column("created_by", sa.String()),
            sa.Column("updated_by", sa.String()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_daily_report_narrative_templates_id", "daily_report_narrative_templates", ["id"])
        op.create_index("ix_daily_report_narrative_templates_category", "daily_report_narrative_templates", ["category"])
        op.create_index("ix_daily_report_narrative_templates_is_active", "daily_report_narrative_templates", ["is_active"])
        op.create_index("ix_daily_report_narrative_templates_sort_order", "daily_report_narrative_templates", ["sort_order"])
        op.create_index("ix_daily_report_narrative_templates_created_at", "daily_report_narrative_templates", ["created_at"])
        op.create_index("ix_daily_report_narrative_templates_updated_at", "daily_report_narrative_templates", ["updated_at"])
    template_table = sa.table(
        "daily_report_narrative_templates",
        sa.column("category", sa.String()),
        sa.column("name", sa.String()),
        sa.column("template_text", sa.Text()),
        sa.column("is_active", sa.Integer()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_by", sa.String()),
        sa.column("updated_by", sa.String()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    template_count = bind.execute(sa.select(sa.func.count()).select_from(template_table)).scalar_one()
    if template_count == 0:
        now = datetime.now()
        op.bulk_insert(template_table, [
            {
                "category": category,
                "name": name,
                "template_text": template_text,
                "is_active": 1,
                "sort_order": sort_order,
                "created_by": "system",
                "updated_by": "system",
                "created_at": now,
                "updated_at": now,
            }
            for category, name, template_text, sort_order in DEFAULT_TEMPLATES
        ])

    inspector = sa.inspect(bind)
    if not inspector.has_table("daily_reports"):
        op.create_table(
            "daily_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("report_date", sa.String(length=10), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("fingerprint", sa.String(), nullable=False),
            sa.Column("generated_at", sa.DateTime()),
            sa.Column("published_at", sa.DateTime()),
            sa.Column("published_by", sa.String()),
            sa.Column("created_by", sa.String()),
            sa.Column("updated_by", sa.String()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.UniqueConstraint("report_date", name="uq_daily_reports_report_date"),
        )
        op.create_index("ix_daily_reports_id", "daily_reports", ["id"])
        op.create_index("ix_daily_reports_report_date", "daily_reports", ["report_date"], unique=True)
        op.create_index("ix_daily_reports_status", "daily_reports", ["status"])
        op.create_index("ix_daily_reports_fingerprint", "daily_reports", ["fingerprint"])
        op.create_index("ix_daily_reports_generated_at", "daily_reports", ["generated_at"])
        op.create_index("ix_daily_reports_published_at", "daily_reports", ["published_at"])
        op.create_index("ix_daily_reports_created_at", "daily_reports", ["created_at"])
        op.create_index("ix_daily_reports_updated_at", "daily_reports", ["updated_at"])


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for daily reports.")
