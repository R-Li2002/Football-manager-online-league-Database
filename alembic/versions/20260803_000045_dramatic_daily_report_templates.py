"""expand dramatic daily report narratives

Revision ID: 20260803_000045
Revises: 20260802_000044
Create Date: 2026-08-03 15:50:00
"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_000045"
down_revision: Union[str, Sequence[str], None] = "20260802_000044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_TEMPLATES = (
    ("narrow_win", "刀尖小胜", "{winner}以 {score} 擦过胜负线，{loser}距离改写结局只差一球。", 30),
    ("regular_win", "把效率写上比分牌", "{winner} {score} 击退 {loser}，用更直接的终结把差距写上比分牌。", 30),
    ("big_win", "三球重创", "{winner} {score} 重创 {loser}，三球以上的优势彻底撕开了双方差距。", 30),
    ("clean_sheet_rout", "火力全开零封到底", "{winner} {score} 零封横扫 {loser}，自己火力全开，也让对手的进球栏始终归零。", 30),
    ("high_scoring_win", "对轰笑到最后", "{winner}在 {total_goals} 球对轰中以 {score} 笑到最后，进攻回击压过了防线失守。", 30),
    ("goalless_draw", "两张白卷", "{home_team}与{away_team}把进球栏锁成 0:0，整场拉扯最终只留下两张白卷。", 30),
    ("draw", "胜果始终缺席", "{home_team}与{away_team}战成 {score}，谁也没能把有限优势真正写成胜果。", 30),
    ("high_scoring_draw", "进球不断赢家缺席", "{home_team}与{away_team}轰出 {score}，合计 {total_goals} 球仍分不出赢家。", 30),
    ("winning_hattrick", "一人接管头条", "{player} 一人轰入三球，几乎以个人名义接管了 {team} 的进攻头条。", 30),
    ("losing_hattrick", "高光撞上残酷结果", "{player} 独中三元却只能目送 {team} 落败，最耀眼的个人演出撞上了最残酷的团队结果。", 30),
    ("brace", "两次破门钉住头条", "{player} 梅开二度，两次破门把名字牢牢钉在 {team} 本场的进攻主线上。", 30),
    ("playmaker", "连续撕开防线", "{player}送出 {assists} 次助攻，用传球连续撕开对手防线。", 30),
    ("goal_and_assist", "一人包办两条火线", "{player} 交出 {goals} 球 {assists} 助攻，一人包办得分与输送两条火线。", 30),
    ("mvp", "压过全场", "{player} 当选本场最佳，用全场最醒目的表现压过了其他竞争者。", 30),
    ("power_upset", "把战力差变成赛前数字", "纸面战力落后的 {winner} 掀翻 {loser}，用结果把 {power_gap} 点差距变成了赛前数字。", 30),
    ("series_sweep", "双杀收走气势", "{winner}两战通吃，以两回合总比分 {aggregate_score} 完成双杀。{first_leg}；{second_leg}，把胜果与气势一并收入囊中。", 10),
    ("series_sweep", "主客场通吃", "{winner}包办两回合胜利，累计以 {aggregate_score} 压过 {loser}。{first_leg}；{second_leg}，主客场都没给对手留下胜果。", 20),
    ("series_split", "针锋相对各守一胜", "{team_a}与{team_b}各赢一场，两回合针锋相对。{first_leg}；{second_leg}，胜负各自带走，悬念谁也没能独占。", 10),
    ("series_split", "隔空对攻", "两回合演成一场隔空对攻：{first_leg}；{second_leg}。{team_a}与{team_b}各守一胜，谁也没能彻底压住对方。", 20),
    ("series_unbeaten", "一胜一平掌控叙事", "{winner}一胜一平保持不败，两回合总比分 {aggregate_score} 占据上风。{first_leg}；{second_leg}，没有让 {loser} 拿走完整胜果。", 10),
    ("series_unbeaten", "不败压住两回合", "{winner}用一胜一平接管两回合叙事：{first_leg}；{second_leg}。不败背后，是总比分 {aggregate_score} 的稳定压制。", 20),
    ("series_draws", "两次交锋停在平局线", "两回合都没有赢家，{team_a}与{team_b}合计打入 {series_goals} 球。{first_leg}；{second_leg}，两次交锋都停在平局线上。", 10),
    ("series_draws", "进球有数赢家缺席", "{team_a}与{team_b}连续两场互不相让：{first_leg}；{second_leg}。总计 {series_goals} 粒进球，仍没人带走胜利。", 20),
)


def upgrade() -> None:
    bind = op.get_bind()
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
    existing = {
        (str(row.category), str(row.name))
        for row in bind.execute(sa.select(template_table.c.category, template_table.c.name))
    }
    now = datetime.now()
    rows = [
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
        for category, name, template_text, sort_order in NEW_TEMPLATES
        if (category, name) not in existing
    ]
    if rows:
        op.bulk_insert(template_table, rows)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for daily report templates.")
