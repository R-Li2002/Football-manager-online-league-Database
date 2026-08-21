"""add draws, season archives, and draw permission

Revision ID: 20260805_000048
Revises: 20260804_000047
Create Date: 2026-08-05 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_000048"
down_revision: Union[str, Sequence[str], None] = "20260804_000047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index(table: str, column: str) -> None:
    op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    coach_columns = {column["name"] for column in inspector.get_columns("coach_accounts")}
    if "can_manage_draws" not in coach_columns:
        with op.batch_alter_table("coach_accounts") as batch_op:
            batch_op.add_column(sa.Column("can_manage_draws", sa.Integer(), nullable=False, server_default="0"))

    if not inspector.has_table("season_archives"):
        op.create_table(
            "season_archives",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("season_key", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("parent_archive_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("validation_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("revision_reason", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("confirmed_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["parent_archive_id"], ["season_archives.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("season_key", "revision_no", name="uq_season_archives_key_revision"),
        )
        for column in ("id", "season_key", "parent_archive_id", "status", "created_by", "confirmed_by", "created_at", "confirmed_at"):
            _index("season_archives", column)

    if not inspector.has_table("draw_sessions"):
        op.create_table(
            "draw_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("draw_type", sa.String(), nullable=False),
            sa.Column("competition", sa.String(), nullable=True),
            sa.Column("season_label", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("random_seed", sa.String(), nullable=False),
            sa.Column("pool_hash", sa.String(), nullable=True),
            sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("candidate_list_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("locked_by", sa.String(), nullable=True),
            sa.Column("completed_by", sa.String(), nullable=True),
            sa.Column("published_by", sa.String(), nullable=True),
            sa.Column("voided_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("voided_at", sa.DateTime(), nullable=True),
            sa.Column("void_reason", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["candidate_list_id"], ["candidate_lists.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("id", "name", "draw_type", "competition", "season_label", "status", "pool_hash", "candidate_list_id", "created_by", "updated_by", "locked_by", "completed_by", "published_by", "voided_by", "created_at", "updated_at", "locked_at", "completed_at", "published_at", "voided_at"):
            _index("draw_sessions", column)

    if not inspector.has_table("draw_pool_entries"):
        op.create_table(
            "draw_pool_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("entity_key", sa.String(), nullable=False),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("player_uid", sa.Integer(), nullable=True),
            sa.Column("entity_name", sa.String(), nullable=False),
            sa.Column("team_name", sa.String(), nullable=True),
            sa.Column("level", sa.String(), nullable=True),
            sa.Column("source_rank", sa.Integer(), nullable=True),
            sa.Column("pot_no", sa.Integer(), nullable=True),
            sa.Column("seed_status", sa.String(), nullable=True),
            sa.Column("self_save_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
            sa.Column("final_value", sa.Float(), nullable=True),
            sa.Column("slot_type", sa.String(), nullable=True),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["draw_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["player_uid"], ["players.uid"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id", "entity_key", name="uq_draw_pool_entries_session_entity"),
        )
        for column in ("id", "session_id", "entity_type", "team_id", "player_uid", "team_name", "level", "pot_no", "seed_status", "is_active"):
            _index("draw_pool_entries", column)

    if not inspector.has_table("draw_picks"):
        op.create_table(
            "draw_picks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("sequence_no", sa.Integer(), nullable=False),
            sa.Column("entry_id", sa.Integer(), nullable=False),
            sa.Column("paired_entry_id", sa.Integer(), nullable=True),
            sa.Column("target_group", sa.String(), nullable=True),
            sa.Column("target_slot", sa.Integer(), nullable=True),
            sa.Column("random_value", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("invalidated_by", sa.String(), nullable=True),
            sa.Column("invalidated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["draw_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["entry_id"], ["draw_pool_entries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["paired_entry_id"], ["draw_pool_entries.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id", "sequence_no", name="uq_draw_picks_session_sequence"),
        )
        for column in ("id", "session_id", "entry_id", "paired_entry_id", "target_group", "status", "created_by", "created_at", "invalidated_by", "invalidated_at"):
            _index("draw_picks", column)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for draw and season archive data.")
