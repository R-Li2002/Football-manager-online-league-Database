"""team cache metadata and indexes

Revision ID: 20260311_000002
Revises: 20260311_000001
Create Date: 2026-03-11 05:10:00
"""

from typing import Sequence, Union

from alembic import op

from database import _configure_engine
from migration_helpers import upgrade_team_cache_schema

# revision identifiers, used by Alembic.
revision: str = "20260311_000002"
down_revision: Union[str, Sequence[str], None] = "20260311_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _configure_engine(bind.engine)
    upgrade_team_cache_schema(bind)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the team cache metadata migration.")
