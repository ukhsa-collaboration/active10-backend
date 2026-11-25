"""create background jobs table

Revision ID: 4a9f9bc1c2d8
Revises: b33e91c25011
Create Date: 2026-07-17 14:02:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a9f9bc1c2d8"  # pragma: allowlist secret
down_revision: Union[str, None] = "b33e91c25011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_background_jobs_id"), "background_jobs", ["id"], unique=False)
    op.create_index(
        op.f("ix_background_jobs_user_id"),
        "background_jobs",
        ["user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_background_jobs_status"), "background_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_background_jobs_status"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_user_id"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_id"), table_name="background_jobs")
    op.drop_table("background_jobs")
