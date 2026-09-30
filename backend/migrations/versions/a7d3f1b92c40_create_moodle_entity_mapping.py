"""create moodle entity mapping

Revision ID: a7d3f1b92c40
Revises: c182a1549dc6
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d3f1b92c40'
down_revision: Union[str, Sequence[str], None] = 'c182a1549dc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('moodle_entity_mappings',
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('internal_id', sa.String(length=255), nullable=False),
    sa.Column('moodle_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_type', 'internal_id', name='uq_moodle_mapping_internal'),
    sa.UniqueConstraint('entity_type', 'moodle_id', name='uq_moodle_mapping_moodle')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('moodle_entity_mappings')