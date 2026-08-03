"""add SOC local user for spot assignment

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-08-03 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision: str = 'j6k7l8m9n0o1'
down_revision: Union[str, Sequence[str], None] = 'i5j6k7l8m9n0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add SOC local user."""
    op.execute(f"""
        INSERT INTO users (id, azure_oid, email, display_name, is_admin, can_manage_guests, can_manage_spots, can_view_reports, password_hash, active)
        VALUES
            ('{uuid4()}', NULL, NULL, 'SOC', false, false, false, false, NULL, true)
        ON CONFLICT (display_name) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema - remove SOC user."""
    op.execute("DELETE FROM users WHERE display_name = 'SOC' AND email IS NULL AND azure_oid IS NULL")
