"""player attribute radar fields

Revision ID: 20260312_000009
Revises: 20260311_000008
Create Date: 2026-03-12 11:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260312_000009"
down_revision: Union[str, Sequence[str], None] = "20260311_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RADAR_COLUMNS = (
    ("radar_defense", sa.Float(), 0.0),
    ("radar_physical", sa.Float(), 0.0),
    ("radar_speed", sa.Float(), 0.0),
    ("radar_creativity", sa.Float(), 0.0),
    ("radar_attack", sa.Float(), 0.0),
    ("radar_technical", sa.Float(), 0.0),
    ("radar_aerial", sa.Float(), 0.0),
    ("radar_mental", sa.Float(), 0.0),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("player_attributes"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("player_attributes")}
    for column_name, column_type, default in RADAR_COLUMNS:
        if column_name in existing_columns:
            continue
        op.add_column(
            "player_attributes",
            sa.Column(column_name, column_type, nullable=False, server_default=sa.text(str(default))),
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player attribute radar fields.")
