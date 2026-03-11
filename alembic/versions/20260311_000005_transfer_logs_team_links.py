"""transfer logs team-link schema and operation constraints

Revision ID: 20260311_000005
Revises: 20260311_000004
Create Date: 2026-03-11 05:16:00
"""

from typing import Sequence, Union

from alembic import op

from database import _configure_engine
from migration_helpers import upgrade_transfer_logs_schema

# revision identifiers, used by Alembic.
revision: str = "20260311_000005"
down_revision: Union[str, Sequence[str], None] = "20260311_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _configure_engine(bind.engine)
    upgrade_transfer_logs_schema(bind, with_backfill=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the transfer log migration.")
