"""matches schedule and results

Revision ID: 20260622_000015
Revises: 20260327_000014
Create Date: 2026-06-22 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260622_000015"
down_revision: Union[str, Sequence[str], None] = "20260327_000014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("matches"):
        return

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_label", sa.String(), nullable=True),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=True),
        sa.Column("home_team_name", sa.String(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=True),
        sa.Column("away_team_name", sa.String(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("match_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matches_id", "matches", ["id"], unique=False)
    op.create_index("ix_matches_season_label", "matches", ["season_label"], unique=False)
    op.create_index("ix_matches_level", "matches", ["level"], unique=False)
    op.create_index("ix_matches_round_no", "matches", ["round_no"], unique=False)
    op.create_index("ix_matches_home_team_id", "matches", ["home_team_id"], unique=False)
    op.create_index("ix_matches_home_team_name", "matches", ["home_team_name"], unique=False)
    op.create_index("ix_matches_away_team_id", "matches", ["away_team_id"], unique=False)
    op.create_index("ix_matches_away_team_name", "matches", ["away_team_name"], unique=False)
    op.create_index("ix_matches_status", "matches", ["status"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for matches.")
