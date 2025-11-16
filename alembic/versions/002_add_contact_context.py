"""Add contact context for natural language intelligence

Revision ID: 002
Revises: 001
Create Date: 2025-11-12 11:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create contact_context table for natural language intelligence
    op.create_table(
        'contact_context',
        sa.Column('contact_id', sa.String(length=100), nullable=False),
        sa.Column('contact_name', sa.String(length=200), nullable=True),
        sa.Column('nicknames', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('personal_notes', sa.Text(), nullable=True),
        sa.Column('company_info', sa.Text(), nullable=True),
        sa.Column('relationship_notes', sa.Text(), nullable=True),
        sa.Column('last_interaction', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('interaction_count', sa.Integer(), default=0),
        sa.Column('importance_score', sa.Integer(), default=5),
        sa.Column('custom_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('contact_id')
    )

    # Indexes for fast searching
    op.create_index('idx_contact_context_nicknames', 'contact_context', ['nicknames'], unique=False, postgresql_using='gin')
    op.create_index('idx_contact_context_name', 'contact_context', ['contact_name'], unique=False)
    op.create_index('idx_contact_context_importance', 'contact_context', ['importance_score'], unique=False)

    # Create interaction_history table for tracking all contact interactions
    op.create_table(
        'interaction_history',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('contact_id', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),  # 'viewed', 'updated', 'called', 'emailed', 'sms'
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_interaction_history_contact', 'interaction_history', ['contact_id', 'timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_interaction_history_type', 'interaction_history', ['interaction_type', 'timestamp'], unique=False, postgresql_ops={'timestamp': 'DESC'})


def downgrade() -> None:
    op.drop_index('idx_interaction_history_type', table_name='interaction_history')
    op.drop_index('idx_interaction_history_contact', table_name='interaction_history')
    op.drop_table('interaction_history')

    op.drop_index('idx_contact_context_importance', table_name='contact_context')
    op.drop_index('idx_contact_context_name', table_name='contact_context')
    op.drop_index('idx_contact_context_nicknames', table_name='contact_context')
    op.drop_table('contact_context')
