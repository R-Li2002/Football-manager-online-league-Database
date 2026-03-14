"""player reactions

Revision ID: 20260314_000011
Revises: 20260312_000010
Create Date: 2026-03-14 03:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260314_000011"
down_revision: Union[str, Sequence[str], None] = "20260312_000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("player_reaction_summaries"):
        op.create_table(
            "player_reaction_summaries",
            sa.Column("player_uid", sa.Integer(), nullable=False),
            sa.Column("flowers", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("eggs", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("flowers >= 0", name="ck_player_reaction_summaries_flowers_non_negative"),
            sa.CheckConstraint("eggs >= 0", name="ck_player_reaction_summaries_eggs_non_negative"),
            sa.ForeignKeyConstraint(["player_uid"], ["player_attributes.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("player_uid"),
        )
        op.create_index(
            "ix_player_reaction_summaries_updated_at",
            "player_reaction_summaries",
            ["updated_at"],
            unique=False,
        )

    if not inspector.has_table("player_reaction_events"):
        op.create_table(
            "player_reaction_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("player_uid", sa.Integer(), nullable=False),
            sa.Column("visitor_token", sa.String(), nullable=False),
            sa.Column("reaction_type", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("reaction_type IN ('flower', 'egg')", name="ck_player_reaction_events_type"),
            sa.ForeignKeyConstraint(["player_uid"], ["player_attributes.uid"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_player_reaction_events_player_uid", "player_reaction_events", ["player_uid"], unique=False)
        op.create_index("ix_player_reaction_events_visitor_token", "player_reaction_events", ["visitor_token"], unique=False)
        op.create_index("ix_player_reaction_events_reaction_type", "player_reaction_events", ["reaction_type"], unique=False)
        op.create_index("ix_player_reaction_events_created_at", "player_reaction_events", ["created_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player reactions.")
