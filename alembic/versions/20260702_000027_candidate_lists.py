"""candidate lists

Revision ID: 20260702_000027
Revises: 20260702_000026
Create Date: 2026-07-02 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_000027"
down_revision: Union[str, Sequence[str], None] = "20260702_000026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("candidate_lists"):
        op.create_table(
            "candidate_lists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("type", sa.String(), nullable=False, server_default="custom"),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("base_data_version", sa.String(), nullable=True),
            sa.Column("source_filters_json", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("published_by", sa.String(), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("archived_by", sa.String(), nullable=True),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("locked_by", sa.String(), nullable=True),
            sa.Column("published_player_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("last_published_snapshot_json", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        for column_name in (
            "id",
            "name",
            "type",
            "status",
            "base_data_version",
            "created_by",
            "updated_by",
            "published_at",
            "published_by",
            "archived_at",
            "archived_by",
            "locked_at",
            "locked_by",
        ):
            op.create_index(f"ix_candidate_lists_{column_name}", "candidate_lists", [column_name], unique=False)

    if not inspector.has_table("candidate_list_players"):
        op.create_table(
            "candidate_list_players",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("list_id", sa.Integer(), nullable=False),
            sa.Column("uid", sa.Integer(), nullable=False),
            sa.Column("data_version", sa.String(), nullable=False),
            sa.Column("name_snapshot", sa.String(), nullable=True),
            sa.Column("club_snapshot", sa.String(), nullable=True),
            sa.Column("heigo_club_snapshot", sa.String(), nullable=True),
            sa.Column("ca_snapshot", sa.Integer(), nullable=True),
            sa.Column("pa_snapshot", sa.Integer(), nullable=True),
            sa.Column("added_by", sa.String(), nullable=True),
            sa.Column("added_at", sa.DateTime(), nullable=True),
            sa.Column("removed_at", sa.DateTime(), nullable=True),
            sa.Column("removed_by", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["list_id"], ["candidate_lists.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        for column_name in ("id", "list_id", "uid", "data_version", "added_by", "removed_at", "removed_by"):
            op.create_index(f"ix_candidate_list_players_{column_name}", "candidate_list_players", [column_name], unique=False)
        op.create_index(
            "ix_candidate_list_players_list_uid_version_removed",
            "candidate_list_players",
            ["list_id", "uid", "data_version", "removed_at"],
            unique=False,
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for candidate lists.")
