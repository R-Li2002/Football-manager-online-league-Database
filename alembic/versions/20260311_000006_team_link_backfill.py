"""players and transfer logs team-link backfill

Revision ID: 20260311_000006
Revises: 20260311_000005
Create Date: 2026-03-11 06:05:00
"""

from typing import Sequence, Union

from alembic import op

from database import _configure_engine
from migration_helpers import backfill_team_link_data

# revision identifiers, used by Alembic.
revision: str = "20260311_000006"
down_revision: Union[str, Sequence[str], None] = "20260311_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _configure_engine(bind.engine)
    backfill_team_link_data(bind)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the team-link backfill migration.")
