"""Create User Activity Level Table

Revision ID: b305b691c836
Revises: 362e0eca0a77
Create Date: 2025-04-16 23:44:05.646372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b305b691c836'
down_revision: Union[str, None] = '362e0eca0a77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_activity_level',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('date', sa.Integer(), nullable=False),
    sa.Column('level', sa.Enum('Inactive', 'Moderately active', 'Active', name='activity_level_enum'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_activity_level_id'), 'user_activity_level', ['id'], unique=False)
    op.create_index(op.f('ix_user_activity_level_user_id'), 'user_activity_level', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_activity_level_user_id'), table_name='user_activity_level')
    op.drop_index(op.f('ix_user_activity_level_id'), table_name='user_activity_level')
    op.drop_table('user_activity_level')
    op.execute('DROP TYPE activity_level_enum')
