from alembic import op
import sqlalchemy as sa


revision = "d3c8a51f9072"
down_revision = "ad8c21f5e9b7"
branch_labels = ("muscle_group",)
depends_on = None


def _validate_existing_table(bind) -> None:
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns("muscle_group")}
    expected = {
        "id": (sa.Integer, False), "name": (sa.String, False),
        "description": (sa.Text, True), "created_by": (sa.BigInteger, True),
    }
    if columns.keys() != expected.keys():
        raise RuntimeError("The existing muscle_group columns are incompatible")
    for name, (column_type, nullable) in expected.items():
        if not isinstance(columns[name]["type"], column_type) or columns[name]["nullable"] != nullable:
            raise RuntimeError(f"The existing muscle_group column {name} is incompatible")
    if isinstance(columns["id"]["type"], (sa.BigInteger, sa.SmallInteger)):
        raise RuntimeError("The muscle_group identifier must be an integer")
    if columns["name"]["type"].length != 150:
        raise RuntimeError("The existing muscle_group name must have a length of 150")
    if columns["id"].get("identity", {}).get("always") is not True:
        raise RuntimeError("The muscle_group identifier must use GENERATED ALWAYS AS IDENTITY")
    if inspector.get_pk_constraint("muscle_group")["constrained_columns"] != ["id"]:
        raise RuntimeError("The existing muscle_group primary key is incompatible")


def _ensure_constraints(bind) -> None:
    inspector = sa.inspect(bind)
    unique = {item["name"]: item for item in inspector.get_unique_constraints("muscle_group")}
    if "uq_muscle_group_name" not in unique:
        op.create_unique_constraint("uq_muscle_group_name", "muscle_group", ["name"])
    elif unique["uq_muscle_group_name"]["column_names"] != ["name"]:
        raise RuntimeError("The existing muscle_group name constraint is incompatible")
    foreign_keys = {item["name"]: item for item in inspector.get_foreign_keys("muscle_group")}
    foreign_key = foreign_keys.get("fk_muscle_group_creator")
    if foreign_key is None:
        op.create_foreign_key(
            "fk_muscle_group_creator", "muscle_group", "app_user",
            ["created_by"], ["id"], ondelete="SET NULL",
        )
    elif (
        foreign_key["constrained_columns"] != ["created_by"]
        or foreign_key["referred_table"] != "app_user"
        or foreign_key["referred_columns"] != ["id"]
        or foreign_key["options"].get("ondelete") != "SET NULL"
    ):
        raise RuntimeError("The existing muscle_group creator constraint is incompatible")


def _ensure_administrator_trigger(bind) -> None:
    trigger = bind.execute(sa.text(
        "SELECT p.proname, t.tgtype, t.tgenabled, ARRAY(SELECT a.attname "
        "FROM pg_attribute a WHERE a.attrelid = t.tgrelid AND a.attnum = ANY(t.tgattr)) AS columns "
        "FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
        "WHERE t.tgrelid = 'muscle_group'::regclass "
        "AND t.tgname = 'trg_muscle_group_admin_only' AND NOT t.tgisinternal"
    )).mappings().first()
    if trigger is not None:
        if (
            trigger["proname"] != "fn_muscle_group_admin_only"
            or trigger["tgtype"] != 23
            or trigger["tgenabled"] not in {"O", "A"}
            or set(trigger["columns"]) != {"created_by"}
        ):
            raise RuntimeError("The existing muscle_group administrator trigger is incompatible")
        return
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_muscle_group_admin_only() RETURNS trigger AS $$
        DECLARE
            creator_role role_user;
        BEGIN
            IF NEW.created_by IS NULL THEN
                IF TG_OP = 'INSERT' THEN
                    RAISE EXCEPTION USING ERRCODE = '23502',
                        MESSAGE = 'A new muscle group requires a creator';
                END IF;
                RETURN NEW;
            END IF;
            SELECT role INTO creator_role FROM app_user WHERE id = NEW.created_by FOR UPDATE;
            IF creator_role IS DISTINCT FROM 'ADMIN' THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001', CONSTRAINT = 'muscle_group_admin_only',
                    MESSAGE = 'Muscle groups require an administrator creator';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_muscle_group_admin_only
        BEFORE INSERT OR UPDATE OF created_by ON muscle_group
        FOR EACH ROW EXECUTE FUNCTION fn_muscle_group_admin_only()
    """)


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("muscle_group"):
        _validate_existing_table(bind)
    else:
        op.create_table(
            "muscle_group",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_by", sa.BigInteger(), nullable=True),
        )
    _ensure_constraints(bind)
    _ensure_administrator_trigger(bind)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_muscle_group_admin_only ON muscle_group")
    op.execute("DROP FUNCTION IF EXISTS fn_muscle_group_admin_only()")
    op.drop_table("muscle_group")
