"""split yellow-card suspension from the next caution cycle

Revision ID: 20260821_000051
Revises: 20260821_000050
Create Date: 2026-08-21 15:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_000051"
down_revision: Union[str, Sequence[str], None] = "20260821_000050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("player_suspension_records"):
        return
    columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
    if "yellow_card_suspended" not in columns:
        op.add_column(
            "player_suspension_records",
            sa.Column("yellow_card_suspended", sa.Integer(), nullable=False, server_default="0"),
        )
    bind.execute(sa.text("""
        UPDATE player_suspension_records
        SET yellow_card_suspended = 1,
            yellow_cards = yellow_cards % 3
        WHERE yellow_cards >= 3
    """))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("player_suspension_records"):
        return
    columns = {column["name"] for column in inspector.get_columns("player_suspension_records")}
    if "yellow_card_suspended" not in columns:
        return
    bind.execute(sa.text("""
        UPDATE player_suspension_records
        SET yellow_cards = yellow_cards + 3
        WHERE yellow_card_suspended = 1
    """))
    op.drop_column("player_suspension_records", "yellow_card_suspended")
