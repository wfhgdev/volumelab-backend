"""create workout set table

Revision ID: 1cd13e65858c
Revises: 704390f96f9b
Create Date: 2026-11-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1cd13e65858c"
down_revision: Union[str, Sequence[str], None] = "704390f96f9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECK_EXPRESSIONS = {
    "chk_set_number": "set_number >= 1",
    "chk_set_order": "exercise_order >= 1",
    "chk_set_reps": "reps IS NULL OR reps >= 1",
    "chk_set_duration": "duration_second IS NULL OR duration_second >= 1",
    "chk_set_rir": "rir IS NULL OR (rir >= 0 AND rir <= 10)",
    "chk_set_effective": "effective_weight_kg IS NULL OR effective_weight_kg > 0",
    "chk_set_one_rm_pct": "one_rm_percentage IS NULL OR one_rm_percentage >= 0",
    "chk_set_reps_xor_duration": "(reps IS NULL) <> (duration_second IS NULL)",
}

INDEX_COLUMNS = {
    "idx_workout_set_session": ["session_id"],
    "idx_workout_set_exercise": ["exercise_id"],
    "idx_workout_set_exercise_session": ["exercise_id", "session_id"],
}

EXPECTED_COLUMNS = {
    "id",
    "session_id",
    "exercise_id",
    "exercise_order",
    "set_number",
    "added_weight_kg",
    "reps",
    "duration_second",
    "rir",
    "note",
    "effective_weight_kg",
    "one_rm_kg",
    "one_rm_percentage",
    "volume_load",
    "completed",
}


def _create_table() -> None:
    op.create_table(
        "workout_set",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("exercise_order", sa.Integer(), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("added_weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("duration_second", sa.Integer(), nullable=True),
        sa.Column("rir", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("effective_weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("one_rm_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("one_rm_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("volume_load", sa.Numeric(12, 3), nullable=True),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_number"], name="chk_set_number"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_order"], name="chk_set_order"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_reps"], name="chk_set_reps"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_duration"], name="chk_set_duration"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_rir"], name="chk_set_rir"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_effective"], name="chk_set_effective"),
        sa.CheckConstraint(CHECK_EXPRESSIONS["chk_set_one_rm_pct"], name="chk_set_one_rm_pct"),
        sa.CheckConstraint(
            CHECK_EXPRESSIONS["chk_set_reps_xor_duration"],
            name="chk_set_reps_xor_duration",
        ),
        sa.UniqueConstraint(
            "session_id",
            "exercise_order",
            "set_number",
            name="uq_workout_set_position",
            deferrable=True,
            initially="IMMEDIATE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workout_session.id"],
            name="fk_workout_set_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["workout.id"],
            name="fk_workout_set_exercise",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="workout_set_pkey"),
    )


def _ensure_constraints(bind) -> None:
    inspector = sa.inspect(bind)
    checks = {item["name"] for item in inspector.get_check_constraints("workout_set")}
    for name, expression in CHECK_EXPRESSIONS.items():
        if name not in checks:
            op.create_check_constraint(name, "workout_set", expression)

    unique = {item["name"] for item in inspector.get_unique_constraints("workout_set")}
    if "uq_workout_set_position" not in unique:
        op.create_unique_constraint(
            "uq_workout_set_position",
            "workout_set",
            ["session_id", "exercise_order", "set_number"],
            deferrable=True,
            initially="IMMEDIATE",
        )

    foreign_keys = {item["name"] for item in inspector.get_foreign_keys("workout_set")}
    if "fk_workout_set_session" not in foreign_keys:
        op.create_foreign_key(
            "fk_workout_set_session",
            "workout_set",
            "workout_session",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if "fk_workout_set_exercise" not in foreign_keys:
        op.create_foreign_key(
            "fk_workout_set_exercise",
            "workout_set",
            "workout",
            ["exercise_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def _ensure_indexes(bind) -> None:
    existing = {item["name"] for item in sa.inspect(bind).get_indexes("workout_set")}
    for name, columns in INDEX_COLUMNS.items():
        if name not in existing:
            op.create_index(name, "workout_set", columns, unique=False)


def _ensure_triggers() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_workout_set_check_type() RETURNS trigger AS $$
        DECLARE
            v_type exercise_type;
        BEGIN
            SELECT type INTO v_type FROM workout WHERE id = NEW.exercise_id;

            IF v_type = 'ISOMETRICO' THEN
                IF NEW.duration_second IS NULL THEN
                    RAISE EXCEPTION 'RN-10: un ejercicio isométrico exige duration_second';
                END IF;
                IF NEW.one_rm_kg IS NOT NULL OR NEW.one_rm_percentage IS NOT NULL THEN
                    RAISE EXCEPTION 'RN-12: el 1RM no aplica a ejercicios isométricos';
                END IF;
            ELSIF v_type = 'DINAMICO' AND NEW.reps IS NULL THEN
                RAISE EXCEPTION 'RN-04: un ejercicio dinámico exige reps';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_check_type ON workout_set")
    op.execute(
        """
        CREATE TRIGGER trg_workout_set_check_type
        BEFORE INSERT OR UPDATE OF exercise_id, reps, duration_second,
            one_rm_kg, one_rm_percentage
        ON workout_set
        FOR EACH ROW EXECUTE FUNCTION fn_workout_set_check_type()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_workout_set_order_exercise() RETURNS trigger AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM workout_set
                WHERE session_id = NEW.session_id
                  AND exercise_order = NEW.exercise_order
                  AND exercise_id <> NEW.exercise_id
                  AND id <> NEW.id
            ) THEN
                RAISE EXCEPTION 'La posición % de la sesión % ya tiene otro ejercicio',
                    NEW.exercise_order, NEW.session_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_order_exercise ON workout_set")
    op.execute(
        """
        CREATE TRIGGER trg_workout_set_order_exercise
        AFTER INSERT OR UPDATE OF session_id, exercise_order, exercise_id
        ON workout_set
        FOR EACH ROW EXECUTE FUNCTION fn_workout_set_order_exercise()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_workout_set_session_open() RETURNS trigger AS $$
        DECLARE
            v_status session_status;
            v_session BIGINT := CASE WHEN TG_OP = 'DELETE' THEN OLD.session_id ELSE NEW.session_id END;
        BEGIN
            SELECT status INTO v_status FROM workout_session WHERE id = v_session;

            IF v_status = 'CERRADO' THEN
                RAISE EXCEPTION 'RN-07: la sesión % está cerrada; sus series no se pueden modificar', v_session;
            END IF;

            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_session_open ON workout_set")
    op.execute(
        """
        CREATE TRIGGER trg_workout_set_session_open
        BEFORE INSERT OR DELETE OR UPDATE ON workout_set
        FOR EACH ROW EXECUTE FUNCTION fn_workout_set_session_open()
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "workout_set" not in inspector.get_table_names():
        _create_table()
        inspector = sa.inspect(bind)
    else:
        existing = {column["name"] for column in inspector.get_columns("workout_set")}
        if not EXPECTED_COLUMNS.issubset(existing):
            raise RuntimeError("The existing workout_set columns do not match the expected schema")

    _ensure_constraints(bind)
    _ensure_indexes(bind)
    _ensure_triggers()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_check_type ON workout_set")
    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_order_exercise ON workout_set")
    op.execute("DROP TRIGGER IF EXISTS trg_workout_set_session_open ON workout_set")
    op.execute("DROP FUNCTION IF EXISTS fn_workout_set_check_type()")
    op.execute("DROP FUNCTION IF EXISTS fn_workout_set_order_exercise()")
    op.execute("DROP FUNCTION IF EXISTS fn_workout_set_session_open()")

    if "workout_set" in inspector.get_table_names():
        op.drop_table("workout_set")
