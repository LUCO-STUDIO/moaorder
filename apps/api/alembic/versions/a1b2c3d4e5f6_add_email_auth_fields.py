"""add email auth fields

Revision ID: a1b2c3d4e5f6
Revises: 9a0fddae8644
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9a0fddae8644"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns (nullable)
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Drop the old NOT NULL + UNIQUE constraint on kakao_id
    op.drop_constraint("users_kakao_id_key", "users", type_="unique")
    op.alter_column("users", "kakao_id", nullable=True)

    # 3. Partial unique indexes (allow NULL, enforce uniqueness only when present)
    op.create_index(
        "ix_users_kakao_id",
        "users",
        ["kakao_id"],
        unique=True,
        postgresql_where=sa.text("kakao_id IS NOT NULL"),
    )
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )

    # 4. CHECK constraint: at least one auth method required
    op.create_check_constraint(
        "ck_users_at_least_one_auth",
        "users",
        "kakao_id IS NOT NULL OR email IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_at_least_one_auth", "users", type_="check")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_kakao_id", table_name="users")

    # Restore original NOT NULL + UNIQUE on kakao_id
    # NOTE: this will fail if any rows have kakao_id IS NULL
    op.alter_column("users", "kakao_id", nullable=False)
    op.create_unique_constraint("users_kakao_id_key", "users", ["kakao_id"])

    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
