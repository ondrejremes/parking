"""add_contact_user_id_to_guest_parkings

Revision ID: f1a2b3c4d5e6
Revises: e7c666db6ae8
Create Date: 2026-07-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e7c666db6ae8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('guest_parkings', sa.Column('contact_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(None, 'guest_parkings', 'users', ['contact_user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'guest_parkings', type_='foreignkey')
    op.drop_column('guest_parkings', 'contact_user_id')
