"""normalize legacy text values

Revision ID: 20260311_000007
Revises: 20260311_000006
Create Date: 2026-03-11 13:35:00
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from domain_types import LEGACY_SLOT_TYPE_MOJIBAKE_VALUES, SLOT_TYPE_FAKE

# revision identifiers, used by Alembic.
revision: str = "20260311_000007"
down_revision: Union[str, Sequence[str], None] = "20260311_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    bind = op.get_bind()
    legacy_slot_literals = ", ".join(_sql_literal(value) for value in LEGACY_SLOT_TYPE_MOJIBAKE_VALUES)
    bind.execute(
        text(
            """
            UPDATE players
            SET slot_type = :normalized_value
            WHERE slot_type IN (__LEGACY_SLOT_VALUES__)
            """
            .replace("__LEGACY_SLOT_VALUES__", legacy_slot_literals)
        ),
        {"normalized_value": SLOT_TYPE_FAKE},
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for legacy text normalization.")
