"""competition work assignment and review

Revision ID: 20260725_000031
Revises: 20260725_000030
Create Date: 2026-07-25 23:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_000031"
down_revision: Union[str, Sequence[str], None] = "20260725_000030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("competition_round_work_states"):
        return

    _add_column_if_missing("competition_round_work_states", sa.Column("assignee_principal_id", sa.String(), nullable=True))
    _add_column_if_missing("competition_round_work_states", sa.Column("assignee_display_name", sa.String(), nullable=True))
    _add_column_if_missing("competition_round_work_states", sa.Column("assigned_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("competition_round_work_states", sa.Column("assigned_by", sa.String(), nullable=True))
    _add_column_if_missing("competition_round_work_states", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("competition_round_work_states", sa.Column("submitted_by", sa.String(), nullable=True))

    existing_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("competition_round_work_states")}
    for name, columns in (
        ("ix_competition_round_work_states_assignee_principal_id", ["assignee_principal_id"]),
        ("ix_competition_round_work_states_assigned_by", ["assigned_by"]),
        ("ix_competition_round_work_states_submitted_by", ["submitted_by"]),
    ):
        if name not in existing_indexes:
            op.create_index(name, "competition_round_work_states", columns)

    if not sa.inspect(bind).has_table("competition_round_work_logs"):
        op.create_table(
            "competition_round_work_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("state_id", sa.Integer(), nullable=False),
            sa.Column("level", sa.String(), nullable=False),
            sa.Column("round_start", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("operator_principal_id", sa.String(), nullable=False),
            sa.Column("operator_display_name", sa.String(), nullable=False),
            sa.Column("from_status", sa.String(), nullable=True),
            sa.Column("to_status", sa.String(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["state_id"], ["competition_round_work_states.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("state_id", "level", "round_start", "action", "operator_principal_id", "created_at"):
            op.create_index(f"ix_competition_round_work_logs_{column}", "competition_round_work_logs", [column])


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for competition work assignment and review.")
