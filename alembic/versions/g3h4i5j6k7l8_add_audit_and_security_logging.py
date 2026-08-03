"""add_audit_and_security_logging

Revision ID: g3h4i5j6k7l8
Revises: f1a2b3c4d5e6
Create Date: 2026-08-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f2e3d4c5b6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('target_resource', sa.String(length=100), nullable=True),
    sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create security_events table
    op.create_table('security_events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for faster queries
    op.create_index('idx_audit_logs_admin_user_id', 'audit_logs', ['admin_user_id'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('idx_security_events_severity', 'security_events', ['severity'])
    op.create_index('idx_security_events_created_at', 'security_events', ['created_at'])
    op.create_index('idx_security_events_ip_address', 'security_events', ['ip_address'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_security_events_ip_address', table_name='security_events')
    op.drop_index('idx_security_events_created_at', table_name='security_events')
    op.drop_index('idx_security_events_severity', table_name='security_events')
    op.drop_index('idx_security_events_event_type', table_name='security_events')
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_admin_user_id', table_name='audit_logs')
    op.drop_table('security_events')
    op.drop_table('audit_logs')
