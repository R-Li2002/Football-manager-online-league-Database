"""record imported team logo sources

Revision ID: 20260730_000040
Revises: 20260730_000039
Create Date: 2026-07-30 23:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_000040"
down_revision: Union[str, Sequence[str], None] = "20260730_000039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("team_logo_sources"):
        return
    op.create_table(
        "team_logo_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="fclogo"),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("source_name", sa.String()),
        sa.Column("source_version", sa.String()),
        sa.Column("source_variant", sa.String()),
        sa.Column("svg_path", sa.String(), nullable=False),
        sa.Column("webp_path", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("matched_query", sa.String()),
        sa.Column("matched_score", sa.Float()),
        sa.Column("imported_by", sa.String()),
        sa.Column("imported_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_logo_sources_id"), "team_logo_sources", ["id"], unique=False)
    op.create_index(op.f("ix_team_logo_sources_team_id"), "team_logo_sources", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_logo_sources_provider"), "team_logo_sources", ["provider"], unique=False)
    op.create_index(op.f("ix_team_logo_sources_sha256"), "team_logo_sources", ["sha256"], unique=False)
    op.create_index(op.f("ix_team_logo_sources_imported_at"), "team_logo_sources", ["imported_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_team_logo_sources_imported_at"), table_name="team_logo_sources")
    op.drop_index(op.f("ix_team_logo_sources_sha256"), table_name="team_logo_sources")
    op.drop_index(op.f("ix_team_logo_sources_provider"), table_name="team_logo_sources")
    op.drop_index(op.f("ix_team_logo_sources_team_id"), table_name="team_logo_sources")
    op.drop_index(op.f("ix_team_logo_sources_id"), table_name="team_logo_sources")
    op.drop_table("team_logo_sources")
