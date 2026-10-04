"""create moodle execution

Revision ID: b3e8c5d41a72
Revises: a7d3f1b92c40
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e8c5d41a72'
down_revision: Union[str, Sequence[str], None] = 'a7d3f1b92c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('moodle_executions',
    sa.Column('operation', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('internal_id', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('moodle_id', sa.Integer(), nullable=True),
    sa.Column('error_category', sa.String(length=30), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_moodle_executions_entity', 'moodle_executions', ['entity_type', 'internal_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_moodle_executions_entity', table_name='moodle_executions')
    op.drop_table('moodle_executions')