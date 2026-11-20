"""create app_user table

Revision ID: ad8c21f5e9b7
Revises: 8b88458469be
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ad8c21f5e9b7"
down_revision: Union[str, Sequence[str], None] = "8b88458469be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE user_gender AS ENUM ('HOMBRE', 'MUJER', 'PREFIERO NO DECIR');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        DO $$ BEGIN
            CREATE TYPE user_status AS ENUM ('ACTIVO', 'BLOQUEADO');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        DO $$ BEGIN
            CREATE TYPE role_user AS ENUM ('ADMIN', 'CLIENTE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))

    if "app_user" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("app_user")}
        if "lastname" not in existing_columns:
            op.add_column("app_user", sa.Column("lastname", sa.String(length=150), nullable=True))
    else:
        op.create_table(
            "app_user",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("lastname", sa.String(length=150), nullable=True),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column(
                "gender",
                postgresql.ENUM("HOMBRE", "MUJER", "PREFIERO NO DECIR", name="user_gender", create_type=False),
                nullable=True,
            ),
            sa.Column(
                "role",
                postgresql.ENUM("ADMIN", "CLIENTE", name="role_user", create_type=False),
                nullable=False,
                server_default=sa.text("'CLIENTE'::role_user"),
            ),
            sa.Column(
                "status",
                postgresql.ENUM("ACTIVO", "BLOQUEADO", name="user_status", create_type=False),
                nullable=False,
                server_default=sa.text("'ACTIVO'::user_status"),
            ),
            sa.Column("height_cm", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.CheckConstraint("birth_date IS NULL OR birth_date <= CURRENT_DATE", name="chk_user_birth_date"),
            sa.CheckConstraint("height_cm IS NULL OR height_cm BETWEEN 50 AND 300", name="chk_user_height"),
            sa.PrimaryKeyConstraint("id"),
        )

    unique_indexes = {
        index["name"]: index
        for index in sa.inspect(bind).get_indexes("app_user")
    }
    if "uq_app_user_email" not in unique_indexes:
        op.execute("CREATE UNIQUE INDEX uq_app_user_email ON app_user (LOWER(email))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_app_user_email")
    op.drop_table("app_user")
    op.execute("DROP TYPE IF EXISTS role_user")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_gender")
