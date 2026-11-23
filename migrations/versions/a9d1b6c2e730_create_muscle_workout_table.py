import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a9d1b6c2e730"
down_revision = None
branch_labels = ("muscle_workout",)
depends_on = ("f2a7c8e9d410", "d3c8a51f9072")


def _validate_existing_table(bind) -> None:
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns("muscle_workout")}
    if set(columns) != {"workout_id", "muscle_group_id", "role_muscular", "weighing"}:
        raise RuntimeError("The existing muscle_workout columns are incompatible")
    for name, column in columns.items():
        if column["nullable"]:
            raise RuntimeError(f"The existing muscle_workout column {name} is incompatible")
        if name != "role_muscular" and (
            not isinstance(column["type"], sa.Integer)
            or isinstance(column["type"], (sa.BigInteger, sa.SmallInteger))
        ):
            raise RuntimeError(f"The existing muscle_workout column {name} must be an integer")
    role_type = columns["role_muscular"]["type"]
    if not isinstance(role_type, postgresql.ENUM) or role_type.name != "muscle_role":
        raise RuntimeError("The existing muscle_workout role type is incompatible")
    primary_key = inspector.get_pk_constraint("muscle_workout")
    if primary_key["constrained_columns"] not in ([], ["workout_id", "muscle_group_id"]):
        raise RuntimeError("The existing muscle_workout primary key is incompatible")


def _ensure_constraints(bind) -> None:
    inspector = sa.inspect(bind)
    if not inspector.get_pk_constraint("muscle_workout")["constrained_columns"]:
        op.create_primary_key("pk_muscle_workout", "muscle_workout", ["workout_id", "muscle_group_id"])
    foreign_keys = {item["name"]: item for item in inspector.get_foreign_keys("muscle_workout")}
    for column, parent in (("workout_id", "workout"), ("muscle_group_id", "muscle_group")):
        name = f"fk_muscle_workout_{parent}"
        existing = foreign_keys.get(name)
        if existing is None:
            op.create_foreign_key(name, "muscle_workout", parent, [column], ["id"], ondelete="CASCADE")
        elif (
            existing["constrained_columns"] != [column]
            or existing["referred_table"] != parent
            or existing["referred_columns"] != ["id"]
            or existing["referred_schema"] not in (None, "public")
            or existing["options"].get("ondelete") != "CASCADE"
        ):
            raise RuntimeError(f"The existing {name} constraint is incompatible")
    expression = (
        "(role_muscular = 'PRIMARIO' AND weighing = 100) OR "
        "(role_muscular = 'SECUNDARIO' AND weighing = 50) OR "
        "(role_muscular = 'TERCIARIO' AND weighing = 10)"
    )
    checks = {item["name"]: item for item in inspector.get_check_constraints("muscle_workout")}
    existing = checks.get("chk_muscle_workout_weighing")
    if existing is None:
        op.create_check_constraint("chk_muscle_workout_weighing", "muscle_workout", expression)
    else:
        def normalize(value):
            without_casts = re.sub(r"::(?:public\.)?muscle_role\b", "", value.lower())
            return without_casts.translate(str.maketrans("", "", "() \t\n\""))

        if normalize(existing["sqltext"]) != normalize(expression):
            raise RuntimeError("The existing muscle_workout weighing constraint is incompatible")
    indexes = {item["name"]: item for item in inspector.get_indexes("muscle_workout")}
    existing = indexes.get("idx_muscle_workout_muscle_group")
    if existing is None:
        op.create_index("idx_muscle_workout_muscle_group", "muscle_workout", ["muscle_group_id"])
    elif existing["column_names"] != ["muscle_group_id"] or existing["unique"]:
        raise RuntimeError("The existing muscle_workout muscle group index is incompatible")


def upgrade() -> None:
    bind = op.get_bind()
    enum = postgresql.ENUM("PRIMARIO", "SECUNDARIO", "TERCIARIO", name="muscle_role", create_type=False)
    existing_enum = next((item for item in sa.inspect(bind).get_enums() if item["name"] == "muscle_role"), None)
    if existing_enum is not None and existing_enum["labels"] != ["PRIMARIO", "SECUNDARIO", "TERCIARIO"]:
        raise RuntimeError("The existing muscle_role enum is incompatible")
    enum.create(bind, checkfirst=True)
    if sa.inspect(bind).has_table("muscle_workout"):
        _validate_existing_table(bind)
    else:
        op.create_table(
            "muscle_workout",
            sa.Column("workout_id", sa.Integer(), nullable=False),
            sa.Column("muscle_group_id", sa.Integer(), nullable=False),
            sa.Column("role_muscular", enum, nullable=False),
            sa.Column("weighing", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("workout_id", "muscle_group_id", name="pk_muscle_workout"),
        )
    _ensure_constraints(bind)


def downgrade() -> None:
    op.drop_index("idx_muscle_workout_muscle_group", table_name="muscle_workout")
    op.drop_table("muscle_workout")
    op.execute("DROP TYPE muscle_role")
