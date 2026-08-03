"""fix migration chain after removing h4i5j6k7l8m9

Revision ID: i5j6k7l8m9n0
Revises: g3h4i5j6k7l8
Create Date: 2026-08-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i5j6k7l8m9n0'
down_revision: Union[str, Sequence[str], None] = 'g3h4i5j6k7l8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove orphaned migration from history."""
    # Remove h4i5j6k7l8m9 from alembic version history if it exists
    # This migration was removed because it was a duplicate of context column in g3h4i5j6k7l8
    op.execute("DELETE FROM alembic_version WHERE version_num = 'h4i5j6k7l8m9'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
