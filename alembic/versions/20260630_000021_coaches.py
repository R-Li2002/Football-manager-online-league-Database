"""coaches

Revision ID: 20260630_000021
Revises: 20260625_000020
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_000021"
down_revision: Union[str, Sequence[str], None] = "20260625_000020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("coaches"):
        op.create_table(
            "coaches",
            sa.Column("uid", sa.String(), nullable=False),
            sa.Column("nickname", sa.String(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_name", sa.String(), nullable=True),
            sa.Column("level", sa.String(), nullable=True),
            sa.Column("avatar_path", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("uid"),
        )
        op.create_index("ix_coaches_uid", "coaches", ["uid"], unique=False)
        op.create_index("ix_coaches_nickname", "coaches", ["nickname"], unique=False)
        op.create_index("ix_coaches_team_id", "coaches", ["team_id"], unique=False)
        op.create_index("ix_coaches_team_name", "coaches", ["team_name"], unique=False)
        op.create_index("ix_coaches_level", "coaches", ["level"], unique=False)

    if not inspector.has_table("coach_honors"):
        op.create_table(
            "coach_honors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("coach_uid", sa.String(), nullable=False),
            sa.Column("season", sa.String(), nullable=True),
            sa.Column("competition", sa.String(), nullable=True),
            sa.Column("honor", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["coach_uid"], ["coaches.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_coach_honors_id", "coach_honors", ["id"], unique=False)
        op.create_index("ix_coach_honors_coach_uid", "coach_honors", ["coach_uid"], unique=False)

    if not inspector.has_table("coach_reaction_summaries"):
        op.create_table(
            "coach_reaction_summaries",
            sa.Column("coach_uid", sa.String(), nullable=False),
            sa.Column("flowers", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("eggs", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("flowers >= 0", name="ck_coach_reaction_summaries_flowers_non_negative"),
            sa.CheckConstraint("eggs >= 0", name="ck_coach_reaction_summaries_eggs_non_negative"),
            sa.ForeignKeyConstraint(["coach_uid"], ["coaches.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("coach_uid"),
        )
        op.create_index("ix_coach_reaction_summaries_coach_uid", "coach_reaction_summaries", ["coach_uid"], unique=False)
        op.create_index("ix_coach_reaction_summaries_updated_at", "coach_reaction_summaries", ["updated_at"], unique=False)

    if not inspector.has_table("coach_reaction_events"):
        op.create_table(
            "coach_reaction_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("coach_uid", sa.String(), nullable=False),
            sa.Column("visitor_token", sa.String(), nullable=False),
            sa.Column("reaction_type", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("reaction_type IN ('flower', 'egg')", name="ck_coach_reaction_events_type"),
            sa.ForeignKeyConstraint(["coach_uid"], ["coaches.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_coach_reaction_events_id", "coach_reaction_events", ["id"], unique=False)
        op.create_index("ix_coach_reaction_events_coach_uid", "coach_reaction_events", ["coach_uid"], unique=False)
        op.create_index("ix_coach_reaction_events_visitor_token", "coach_reaction_events", ["visitor_token"], unique=False)
        op.create_index("ix_coach_reaction_events_reaction_type", "coach_reaction_events", ["reaction_type"], unique=False)
        op.create_index("ix_coach_reaction_events_created_at", "coach_reaction_events", ["created_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for coaches.")
