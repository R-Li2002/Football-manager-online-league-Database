"""ranking system

Revision ID: 20260802_000043
Revises: 20260801_000042
Create Date: 2026-08-02 00:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260802_000043"
down_revision: Union[str, Sequence[str], None] = "20260801_000042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("coach_accounts"):
        columns = {column["name"] for column in inspector.get_columns("coach_accounts")}
        if "can_manage_rankings" not in columns:
            op.add_column(
                "coach_accounts",
                sa.Column("can_manage_rankings", sa.Integer(), nullable=False, server_default=sa.text("0")),
            )

    if not inspector.has_table("ranking_seeds"):
        op.create_table(
            "ranking_seeds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
            sa.Column("team_name", sa.String(), nullable=False),
            sa.Column("base_points", sa.Float(), nullable=False, server_default=sa.text("1000")),
            sa.Column("matches", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("wins", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("draws", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("losses", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("source_name", sa.String()),
            sa.Column("source_row", sa.Integer()),
            sa.Column("imported_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.UniqueConstraint("team_id", name="uq_ranking_seeds_team_id"),
        )
        op.create_index("ix_ranking_seeds_id", "ranking_seeds", ["id"])
        op.create_index("ix_ranking_seeds_team_id", "ranking_seeds", ["team_id"], unique=True)

    inspector = sa.inspect(bind)
    if not inspector.has_table("ranking_matches"):
        op.create_table(
            "ranking_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="SET NULL")),
            sa.Column("home_team_name", sa.String(), nullable=False),
            sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="SET NULL")),
            sa.Column("away_team_name", sa.String(), nullable=False),
            sa.Column("home_score", sa.Integer(), nullable=False),
            sa.Column("away_score", sa.Integer(), nullable=False),
            sa.Column("created_by", sa.String()),
            sa.Column("played_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("home_score >= 0", name="ck_ranking_matches_home_score_non_negative"),
            sa.CheckConstraint("away_score >= 0", name="ck_ranking_matches_away_score_non_negative"),
            sa.CheckConstraint("home_team_id != away_team_id", name="ck_ranking_matches_distinct_teams"),
        )
        op.create_index("ix_ranking_matches_id", "ranking_matches", ["id"])
        op.create_index("ix_ranking_matches_home_team_id", "ranking_matches", ["home_team_id"])
        op.create_index("ix_ranking_matches_away_team_id", "ranking_matches", ["away_team_id"])
        op.create_index("ix_ranking_matches_played_at", "ranking_matches", ["played_at"])


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for ranking system.")
