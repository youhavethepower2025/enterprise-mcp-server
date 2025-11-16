"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-11-12 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tool_executions table
    op.create_table(
        'tool_executions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=True),
        sa.Column('user_context', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tool_executions_timestamp', 'tool_executions', ['timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_tool_executions_tool_name', 'tool_executions', ['tool_name', 'timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})

    # Create api_calls table
    op.create_table(
        'api_calls',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ecosystem', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('request_size_bytes', sa.Integer(), nullable=True),
        sa.Column('response_size_bytes', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('rate_limited', sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_calls_ecosystem', 'api_calls', ['ecosystem', 'timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_api_calls_timestamp', 'api_calls', ['timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})

    # Create contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('ecosystem', sa.String(length=50), nullable=False, default='gohighlevel'),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('last_synced', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_contacts_last_synced', 'contacts', ['last_synced'], unique=False, postgresql_ops={'last_synced': 'DESC'})

    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('ecosystem', sa.String(length=50), nullable=False, default='quickbooks'),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('last_synced', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_invoices_last_synced', 'invoices', ['last_synced'], unique=False, postgresql_ops={'last_synced': 'DESC'})

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('ecosystem', sa.String(length=50), nullable=False, default='amazon'),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('last_synced', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orders_last_synced', 'orders', ['last_synced'], unique=False, postgresql_ops={'last_synced': 'DESC'})


def downgrade() -> None:
    op.drop_index('idx_orders_last_synced', table_name='orders')
    op.drop_table('orders')
    op.drop_index('idx_invoices_last_synced', table_name='invoices')
    op.drop_table('invoices')
    op.drop_index('idx_contacts_last_synced', table_name='contacts')
    op.drop_table('contacts')
    op.drop_index('idx_api_calls_timestamp', table_name='api_calls')
    op.drop_index('idx_api_calls_ecosystem', table_name='api_calls')
    op.drop_table('api_calls')
    op.drop_index('idx_tool_executions_tool_name', table_name='tool_executions')
    op.drop_index('idx_tool_executions_timestamp', table_name='tool_executions')
    op.drop_table('tool_executions')
