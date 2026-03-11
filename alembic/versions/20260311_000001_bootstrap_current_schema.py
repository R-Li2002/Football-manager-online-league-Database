"""bootstrap current schema

Revision ID: 20260311_000001
Revises:
Create Date: 2026-03-11 04:30:00
"""

from typing import Sequence, Union

from alembic import op

from database import Base, _configure_engine
import models  # noqa: F401  # Load ORM models so Base.metadata includes all tables.

# revision identifiers, used by Alembic.
revision: str = "20260311_000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _configure_engine(bind.engine)
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the bootstrap migration.")
