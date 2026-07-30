"""competition responsibility assignments

Revision ID: 20260726_000032
Revises: 20260725_000031
Create Date: 2026-07-26 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260726_000032"
down_revision: Union[str, Sequence[str], None] = "20260725_000031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("competition_responsibility_assignments"):
        return
    op.create_table(
        "competition_responsibility_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("responsibility_type", sa.String(), nullable=False),
        sa.Column("principal_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("assigned_by", sa.String(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level", "responsibility_type", name="uq_competition_responsibility_level_type"),
    )
    for column in ("level", "responsibility_type", "principal_id", "assigned_by"):
        op.create_index(
            f"ix_competition_responsibility_assignments_{column}",
            "competition_responsibility_assignments",
            [column],
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for competition responsibilities.")
