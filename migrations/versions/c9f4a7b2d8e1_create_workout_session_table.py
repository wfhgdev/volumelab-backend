"""create workout_session table

Revision ID: c9f4a7b2d8e1
Revises: b04e53ddb8e3
Create Date: 2026-11-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c9f4a7b2d8e1"
down_revision: Union[str, Sequence[str], None] = "b04e53ddb8e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if bind.dialect.name == "postgresql":
        postgresql.ENUM("ABIERTO", "CERRADO", name="session_status").create(bind, checkfirst=True)

    if "workout_session" not in tables:
        op.create_table(
            "workout_session",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("week_id", sa.BigInteger(), nullable=True),
            sa.Column("title", sa.String(length=200), nullable=True),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("current_bodyweight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column("observation", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column(
                "status",
                sa.Enum("ABIERTO", "CERRADO", name="session_status", create_type=False),
                server_default="ABIERTO",
                nullable=False,
            ),
            sa.CheckConstraint("(status = 'CERRADO') = (closed_at IS NOT NULL)", name="chk_session_closed"),
            sa.CheckConstraint(
                "current_bodyweight_kg IS NULL OR current_bodyweight_kg > 0",
                name="chk_session_snapshot",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], name="fk_workout_session_user", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["week_id"],
                ["training_week.id"],
                name="fk_workout_session_week",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id", name="workout_session_pkey"),
        )
        inspector = sa.inspect(bind)

    index_names = {index["name"] for index in inspector.get_indexes("workout_session")}
    if "idx_workout_session_user_date" not in index_names:
        op.execute(
            "CREATE INDEX idx_workout_session_user_date "
            "ON workout_session (user_id, session_date DESC)"
        )
    if "idx_workout_session_week" not in index_names:
        op.create_index("idx_workout_session_week", "workout_session", ["week_id"], unique=False)

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION fn_session_client_limit()
            RETURNS trigger AS $$
            DECLARE
                v_role role_user;
                v_public_count integer;
            BEGIN
                SELECT role INTO v_role FROM app_user WHERE id = NEW.user_id FOR UPDATE;

                IF v_role = 'CLIENTE' AND NEW.public THEN
                    IF TG_OP = 'UPDATE' THEN
                        SELECT COUNT(*) INTO v_public_count
                        FROM workout_session
                        WHERE user_id = NEW.user_id
                          AND public = TRUE
                          AND id <> NEW.id;
                    ELSE
                        SELECT COUNT(*) INTO v_public_count
                        FROM workout_session
                        WHERE user_id = NEW.user_id
                          AND public = TRUE;
                    END IF;

                    IF v_public_count >= 20 THEN
                        RAISE EXCEPTION 'RN-17: CLIENTE cannot have more than 20 public workout sessions';
                    END IF;
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_session_client_limit ON workout_session")
        op.execute(
            """
            CREATE TRIGGER trg_session_client_limit
            BEFORE INSERT OR UPDATE OF user_id, public
            ON workout_session
            FOR EACH ROW
            EXECUTE FUNCTION fn_session_client_limit();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_session_client_limit ON workout_session")
        op.execute("DROP FUNCTION IF EXISTS fn_session_client_limit()")

    if "workout_session" in inspector.get_table_names():
        index_names = {index["name"] for index in inspector.get_indexes("workout_session")}
        if "idx_workout_session_week" in index_names:
            op.drop_index("idx_workout_session_week", table_name="workout_session")
        if "idx_workout_session_user_date" in index_names:
            op.drop_index("idx_workout_session_user_date", table_name="workout_session")
        op.drop_table("workout_session")

    if bind.dialect.name == "postgresql":
        postgresql.ENUM("ABIERTO", "CERRADO", name="session_status").drop(bind, checkfirst=True)
