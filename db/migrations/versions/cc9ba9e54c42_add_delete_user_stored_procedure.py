"""Add delete_user stored procedure

Revision ID: cc9ba9e54c42
Revises: 162a50d9f084
Create Date: 2024-08-22 18:56:47.604531

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'cc9ba9e54c42'
down_revision: Union[str, None] = '162a50d9f084'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

stored_procedure_sql = """
CREATE OR REPLACE FUNCTION delete_user_by_id(user_id UUID)
RETURNS VOID AS $$
BEGIN
    SET TIME ZONE 'UTC';
    DELETE FROM users WHERE id = user_id;

    INSERT INTO delete_audit (id, user_id, delete_reason, deleted_at) 
    VALUES (gen_random_uuid(), user_id, 'Logout deleted after 365 days', NOW());
END;
$$ LANGUAGE plpgsql;
"""



def upgrade() -> None:
    if op.get_bind().execute(text("SELECT to_regclass('public.users')")).scalar() is not None:
        op.execute(text(stored_procedure_sql))


def downgrade() -> None:
    op.execute(text("DROP FUNCTION IF EXISTS delete_user_by_id(UUID);"))
