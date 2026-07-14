"""make email nullable and add system accounts

Revision ID: 001_system_accounts
Revises: e7c666db6ae8
Create Date: 2026-07-14 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision: str = '001_system_accounts'
down_revision: Union[str, Sequence[str], None] = 'e7c666db6ae8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make email nullable
    op.alter_column('users', 'email', existing_type=sa.String(255), nullable=True)

    # Remove unique constraint on email (since it can be NULL now)
    op.drop_constraint('users_email_key', 'users', type_='unique')

    # Insert system accounts
    op.execute(f"""
        INSERT INTO users (id, azure_oid, email, display_name, is_admin, can_manage_guests, can_manage_spots, can_view_reports, password_hash)
        VALUES
            ('{uuid4()}', NULL, NULL, 'Technici', false, false, false, false, NULL),
            ('{uuid4()}', NULL, NULL, 'Backoffice', false, false, false, false, NULL)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove system accounts
    op.execute("DELETE FROM users WHERE display_name IN ('Technici', 'Backoffice') AND email IS NULL")

    # Recreate unique constraint on email
    op.create_unique_constraint('users_email_key', 'users', ['email'])

    # Make email NOT NULL again
    op.alter_column('users', 'email', existing_type=sa.String(255), nullable=False)
