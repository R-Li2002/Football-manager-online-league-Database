"""track league matches served by active suspensions

Revision ID: 20260823_000053
Revises: 20260823_000052
Create Date: 2026-08-23 14:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_000053"
down_revision: Union[str, Sequence[str], None] = "20260823_000052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("player_suspension_records"):
        columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
        if "suspension_started_at" not in columns:
            op.add_column(
                "player_suspension_records",
                sa.Column("suspension_started_at", sa.DateTime(), nullable=True),
            )

    if not inspector.has_table("player_suspension_served_matches"):
        op.create_table(
            "player_suspension_served_matches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("suspension_record_id", sa.Integer(), nullable=False),
            sa.Column("match_id", sa.Integer(), nullable=False),
            sa.Column("served_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["match_id"],
                ["matches.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["suspension_record_id"],
                ["player_suspension_records.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "suspension_record_id",
                "match_id",
                name="uq_suspension_served_record_match",
            ),
        )
        op.create_index(
            op.f("ix_player_suspension_served_matches_match_id"),
            "player_suspension_served_matches",
            ["match_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_player_suspension_served_matches_suspension_record_id"),
            "player_suspension_served_matches",
            ["suspension_record_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("player_suspension_served_matches"):
        op.drop_index(
            op.f("ix_player_suspension_served_matches_suspension_record_id"),
            table_name="player_suspension_served_matches",
        )
        op.drop_index(
            op.f("ix_player_suspension_served_matches_match_id"),
            table_name="player_suspension_served_matches",
        )
        op.drop_table("player_suspension_served_matches")

    inspector = sa.inspect(bind)
    if inspector.has_table("player_suspension_records"):
        columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
        if "suspension_started_at" in columns:
            op.drop_column("player_suspension_records", "suspension_started_at")
