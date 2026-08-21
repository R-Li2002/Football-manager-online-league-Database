"""normalize league forfeit scores

Revision ID: 20260821_000050
Revises: 20260805_000049
Create Date: 2026-08-21 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_000050"
down_revision: Union[str, Sequence[str], None] = "20260805_000049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("matches"):
        return
    bind.execute(sa.text("UPDATE matches SET home_score = 0, away_score = 0 WHERE status = 'home_forfeit'"))
    bind.execute(sa.text("UPDATE matches SET home_score = 2, away_score = 0 WHERE status = 'away_forfeit'"))
    bind.execute(sa.text("UPDATE matches SET home_score = 0, away_score = 0 WHERE status = 'double_forfeit'"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("matches"):
        return
    bind.execute(sa.text("UPDATE matches SET home_score = 0, away_score = 0 WHERE status = 'home_forfeit'"))
    bind.execute(sa.text("UPDATE matches SET home_score = 3, away_score = 0 WHERE status = 'away_forfeit'"))
    bind.execute(sa.text("UPDATE matches SET home_score = 0, away_score = 0 WHERE status = 'double_forfeit'"))
