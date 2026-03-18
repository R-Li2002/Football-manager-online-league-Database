"""player attribute versions

Revision ID: 20260318_000012
Revises: 20260314_000011
Create Date: 2026-03-18 01:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from attribute_versions import DEFAULT_ATTRIBUTE_DATA_VERSION
from database import _configure_engine
import models


# revision identifiers, used by Alembic.
revision: str = "20260318_000012"
down_revision: Union[str, Sequence[str], None] = "20260314_000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _configure_engine(bind.engine)
    models.PlayerAttributeVersion.__table__.create(bind=bind, checkfirst=True)

    inspector = sa.inspect(bind)
    if not inspector.has_table("player_attributes") or not inspector.has_table("player_attribute_versions"):
        return

    existing_count = bind.execute(sa.text("SELECT COUNT(*) FROM player_attribute_versions")).scalar() or 0
    if existing_count:
        return

    source_columns = [column["name"] for column in inspector.get_columns("player_attributes")]
    if not source_columns:
        return

    insert_columns = source_columns + ["data_version"]
    insert_column_sql = ", ".join(insert_columns)
    select_column_sql = ", ".join(source_columns)
    bind.execute(
        sa.text(
            f"""
            INSERT INTO player_attribute_versions ({insert_column_sql})
            SELECT {select_column_sql}, :data_version
            FROM player_attributes
            """
        ),
        {"data_version": DEFAULT_ATTRIBUTE_DATA_VERSION},
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for player attribute versions.")
