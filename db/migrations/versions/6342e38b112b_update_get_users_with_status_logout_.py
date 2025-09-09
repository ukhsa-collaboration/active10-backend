"""update get_users_with_status_logout stored procedure

Revision ID: 6342e38b112b
Revises: aa8451fd521c
Create Date: 2024-09-19 21:21:18.256479

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "6342e38b112b"
down_revision: Union[str, None] = "aa8451fd521c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

stored_procedure_sql = """
CREATE OR REPLACE FUNCTION get_users_with_status_logout()
RETURNS TABLE(id UUID, email VARCHAR, status VARCHAR, status_updated_at TIMESTAMP, first_name VARCHAR) AS $$
BEGIN
    SET TIME ZONE 'UTC';
    RETURN QUERY
    SELECT u.id, u.email, u.status, u.status_updated_at, u.first_name
    FROM users u
    WHERE u.status = 'Logout'
    AND (
        DATE(u.status_updated_at) = DATE(NOW() - INTERVAL '6 months')
        OR DATE(u.status_updated_at) = DATE(NOW() - INTERVAL '9 months')
        OR DATE(u.status_updated_at) = DATE(NOW() - INTERVAL '51 weeks')
        OR DATE(u.status_updated_at) = DATE(NOW() - INTERVAL '1 year')
    );
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    if (
        op.get_bind().execute(text("SELECT to_regclass('public.users')")).scalar()
        is not None
    ):
        op.execute(text(stored_procedure_sql))


def downgrade():
    op.execute(text("DROP FUNCTION IF EXISTS get_users_with_status_logout();"))
