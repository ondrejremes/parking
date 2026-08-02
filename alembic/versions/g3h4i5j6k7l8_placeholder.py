"""Placeholder migration to sync database state."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
