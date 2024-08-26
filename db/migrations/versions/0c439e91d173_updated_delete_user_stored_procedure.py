"""updated delete_user stored procedure

Revision ID: 0c439e91d173
Revises: cc9ba9e54c42
Create Date: 2024-08-26 20:08:27.192485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '0c439e91d173'
down_revision: Union[str, None] = 'cc9ba9e54c42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


stored_procedure_sql = """
DROP FUNCTION IF EXISTS delete_user_by_id(UUID);
CREATE OR REPLACE FUNCTION delete_user_by_id(user_id UUID)
RETURNS TABLE(user_deleted INT, audit_count INT) AS $$
DECLARE
    delete_count INT := 0;
    insert_count INT := 0;
BEGIN
    SET TIME ZONE 'UTC';

    DELETE FROM users WHERE id = user_id RETURNING 1 INTO delete_count;

    IF delete_count = 1 THEN
        INSERT INTO delete_audit (id, user_id, delete_reason, deleted_at) 
        VALUES (gen_random_uuid(), user_id, 'Logout deleted after 365 days', NOW())
        RETURNING 1 INTO insert_count;
    END IF;

    RETURN QUERY SELECT delete_count AS user_deleted, insert_count AS audit_count;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    if op.get_bind().execute(text("SELECT to_regclass('public.users')")).scalar() is not None:
        op.execute(text(stored_procedure_sql))


def downgrade() -> None:
    op.execute(text("DROP FUNCTION IF EXISTS delete_user_by_id(UUID);"))
