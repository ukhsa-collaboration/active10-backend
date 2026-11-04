"""add keycloak_sub and nhs_number index to users

Revision ID: 038267b92c35
Revises: b33e91c25011
Create Date: 2026-10-15 17:16:31.711462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '038267b92c35'
down_revision: Union[str, None] = 'b33e91c25011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('keycloak_sub', sa.String(length=64), nullable=True))
    with op.get_context().autocommit_block():
        op.create_index(
            op.f('ix_users_keycloak_sub'),
            'users',
            ['keycloak_sub'],
            unique=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            op.f('ix_users_nhs_number'),
            'users',
            ['nhs_number'],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            op.f('ix_users_nhs_number'), table_name='users', postgresql_concurrently=True
        )
        op.drop_index(
            op.f('ix_users_keycloak_sub'), table_name='users', postgresql_concurrently=True
        )
    op.drop_column('users', 'keycloak_sub')
