from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f2a7c8e9d410"
down_revision = "ad8c21f5e9b7"
branch_labels = ("workout",)
depends_on = None


def _validate_existing_table(bind) -> None:
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns("workout")}
    expected = {
        "id": (sa.Integer, False), "name": (sa.String, False),
        "description": (sa.Text, True), "type": (postgresql.ENUM, False),
        "is_bodyweight": (sa.Boolean, False), "allow_positive_ballast": (sa.Boolean, False),
        "allow_negative_ballast": (sa.Boolean, False), "public": (sa.Boolean, False),
        "state": (sa.Boolean, False), "created_by": (sa.BigInteger, True),
    }
    if columns.keys() != expected.keys():
        raise RuntimeError("The existing workout columns do not match the expected schema")
    for name, (column_type, nullable) in expected.items():
        column = columns[name]
        if not isinstance(column["type"], column_type) or column["nullable"] != nullable:
            raise RuntimeError(f"The existing workout column {name} is incompatible")
    if isinstance(columns["id"]["type"], sa.BigInteger):
        raise RuntimeError("The existing workout identifier must be an integer")
    if columns["name"]["type"].length != 200:
        raise RuntimeError("The existing workout name must have a length of 200")
    if columns["type"]["type"].name != "exercise_type":
        raise RuntimeError("The existing workout type must use exercise_type")
    if columns["id"].get("identity", {}).get("always") is not True:
        raise RuntimeError("The existing workout identifier must use GENERATED ALWAYS AS IDENTITY")
    if inspector.get_pk_constraint("workout")["constrained_columns"] != ["id"]:
        raise RuntimeError("The existing workout primary key is incompatible")
    for name, expected_default in {
        "is_bodyweight": "false", "allow_positive_ballast": "true",
        "allow_negative_ballast": "false", "public": "false", "state": "true",
    }.items():
        if str(columns[name]["default"]).lower() != expected_default:
            raise RuntimeError(f"The existing default for workout.{name} is incompatible")


def _ensure_constraints(bind) -> None:
    inspector = sa.inspect(bind)
    unique = {item["name"]: item for item in inspector.get_unique_constraints("workout")}
    if "uq_workout_name" not in unique:
        op.create_unique_constraint("uq_workout_name", "workout", ["name"])
    elif unique["uq_workout_name"]["column_names"] != ["name"]:
        raise RuntimeError("The existing workout name constraint is incompatible")
    checks = {item["name"]: item for item in inspector.get_check_constraints("workout")}
    if "chk_workout_negative_ballast" not in checks:
        op.create_check_constraint("chk_workout_negative_ballast", "workout",
                                   "NOT allow_negative_ballast OR is_bodyweight")
    else:
        expression = checks["chk_workout_negative_ballast"]["sqltext"]
        normalized = expression.lower().translate(str.maketrans("", "", "() \t\n"))
        if normalized != "notallow_negative_ballastoris_bodyweight":
            raise RuntimeError("The existing workout ballast constraint is incompatible")
    foreign_keys = {item["name"]: item for item in inspector.get_foreign_keys("workout")}
    foreign_key = foreign_keys.get("fk_workout_creator")
    if foreign_key is None:
        op.create_foreign_key("fk_workout_creator", "workout", "app_user", ["created_by"], ["id"], ondelete="SET NULL")
    elif (
            foreign_key["constrained_columns"] != ["created_by"]
            or foreign_key["referred_table"] != "app_user"
            or foreign_key["referred_columns"] != ["id"]
            or foreign_key["options"].get("ondelete") != "SET NULL"
    ):
        raise RuntimeError("The existing workout creator foreign key is incompatible")
    indexes = {item["name"]: item for item in inspector.get_indexes("workout")}
    if "idx_workout_created_by" not in indexes:
        op.create_index("idx_workout_created_by", "workout", ["created_by"])
    elif (
        indexes["idx_workout_created_by"]["column_names"] != ["created_by"]
        or indexes["idx_workout_created_by"]["unique"]
    ):
        raise RuntimeError("The existing workout creator index is incompatible")


def _ensure_public_limit_trigger(bind) -> None:
    trigger = bind.execute(sa.text(
        "SELECT p.proname, t.tgtype, t.tgenabled, ARRAY(SELECT a.attname "
        "FROM pg_attribute a WHERE a.attrelid = t.tgrelid AND a.attnum = ANY(t.tgattr)) AS columns "
        "FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
        "WHERE t.tgrelid = 'workout'::regclass AND t.tgname = 'trg_workout_client_limit' AND NOT t.tgisinternal"
    )).mappings().first()
    if trigger is not None:
        if (
            trigger["proname"] != "fn_workout_client_limit"
            or trigger["tgtype"] != 23
            or trigger["tgenabled"] not in {"O", "A"}
            or set(trigger["columns"]) != {"created_by", "public"}
        ):
            raise RuntimeError("The existing workout public limit trigger is incompatible")
        return
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_workout_client_limit() RETURNS trigger AS $$
        DECLARE
            creator_role role_user;
            public_count integer;
        BEGIN
            IF NEW.created_by IS NULL THEN
                IF TG_OP = 'INSERT' THEN
                    RAISE EXCEPTION USING ERRCODE = '23502', MESSAGE = 'A new workout requires a creator';
                END IF;
                RETURN NEW;
            END IF;
            IF NOT NEW.public THEN
                RETURN NEW;
            END IF;
            SELECT role INTO creator_role FROM app_user WHERE id = NEW.created_by FOR UPDATE;
            IF creator_role = 'CLIENTE' THEN
                SELECT COUNT(*) INTO public_count FROM workout
                WHERE created_by = NEW.created_by AND public AND id <> NEW.id;
                IF public_count >= 20 THEN
                    RAISE EXCEPTION USING ERRCODE = 'P0001', CONSTRAINT = 'workout_public_limit',
                        MESSAGE = 'A client can have at most 20 public workouts';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_workout_client_limit
        BEFORE INSERT OR UPDATE OF created_by, public ON workout
        FOR EACH ROW EXECUTE FUNCTION fn_workout_client_limit()
    """)


def upgrade() -> None:
    bind = op.get_bind()
    enum = postgresql.ENUM("DINAMICO", "ISOMETRICO", name="exercise_type", create_type=False)
    existing_enum = next((item for item in sa.inspect(bind).get_enums() if item["name"] == "exercise_type"), None)
    if existing_enum is not None and existing_enum["labels"] != ["DINAMICO", "ISOMETRICO"]:
        raise RuntimeError("The existing exercise_type enum is incompatible")
    enum.create(bind, checkfirst=True)
    if sa.inspect(bind).has_table("workout"):
        _validate_existing_table(bind)
    else:
        op.create_table(
            "workout",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("type", enum, nullable=False),
            sa.Column("is_bodyweight", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("allow_positive_ballast", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("allow_negative_ballast", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("state", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.BigInteger(), nullable=True),
        )
    _ensure_constraints(bind)
    _ensure_public_limit_trigger(bind)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_workout_client_limit ON workout")
    op.execute("DROP FUNCTION IF EXISTS fn_workout_client_limit()")
    op.drop_index("idx_workout_created_by", table_name="workout")
    op.drop_table("workout")
    op.execute("DROP TYPE exercise_type")
