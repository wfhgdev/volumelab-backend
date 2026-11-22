from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.controllers import muscle_workout_controller as controller
from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.muscle_group_model import MuscleGroupModel
from app.models.muscle_workout_model import MuscleRole, MuscleWorkoutModel
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.muscle_workout_schema import MuscleWorkoutCreate, MuscleWorkoutUpdate
from tests.postgres_fixtures import migrate_database


pytestmark = pytest.mark.postgres


def seed_catalog(db):
    admin = AppUserModel(name="Admin", email="admin@example.com", password_hash="test", role="ADMIN", status="ACTIVO")
    db.add(admin)
    db.flush()
    workout = WorkoutModel(name="Squat", type=ExerciseType.DYNAMIC, created_by=admin.id)
    group = MuscleGroupModel(name="Legs", created_by=admin.id)
    db.add_all([workout, group])
    db.commit()
    return workout.id, group.id


def payload(keys):
    return MuscleWorkoutCreate(workout_id=keys[0], muscle_group_id=keys[1], muscle_role=MuscleRole.PRIMARY)


def create_series_table(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE workout_set (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
            "exercise_id integer NOT NULL REFERENCES workout(id) ON DELETE RESTRICT)"
        ))


@pytest.fixture(scope="module")
def association_engine(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_workout@head")
        create_series_table(engine)
        yield engine


@pytest.fixture
def postgres_catalog(association_engine):
    with association_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as db:
            try:
                yield db, seed_catalog(db)
            finally:
                db.close()
                transaction.rollback()


def test_migration_preserves_parent_labels_and_reverses_only_association(postgres_database_factory):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    graph = ScriptDirectory.from_config(config)
    assert graph.get_revision("workout@head").revision == "f2a7c8e9d410"
    assert graph.get_revision("muscle_group@head").revision == "d3c8a51f9072"
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_workout@head")
        inspector = inspect(engine)
        assert inspector.get_pk_constraint("muscle_workout")["constrained_columns"] == ["workout_id", "muscle_group_id"]
        assert len(inspector.get_columns("muscle_workout")) == 4
        with Session(engine) as db:
            keys = seed_catalog(db)
        migrate_database(engine, "muscle_workout@-1", downgrade=True)
        assert not inspect(engine).has_table("muscle_workout")
        assert inspect(engine).has_table("workout")
        assert inspect(engine).has_table("muscle_group")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM workout WHERE id = :id"), {"id": keys[0]}).scalar_one() == 1
            assert connection.execute(text("SELECT COUNT(*) FROM muscle_group WHERE id = :id"), {"id": keys[1]}).scalar_one() == 1
        migrate_database(engine, "muscle_workout@head")
        assert inspect(engine).has_table("muscle_workout")


def test_migration_adopts_existing_tables_and_data(postgres_database_factory):
    with postgres_database_factory() as engine:
        for table in (AppUserModel.__table__, WorkoutModel.__table__, MuscleGroupModel.__table__, MuscleWorkoutModel.__table__):
            table.create(engine)
        with Session(engine) as db:
            keys = seed_catalog(db)
            db.add(MuscleWorkoutModel(workout_id=keys[0], muscle_group_id=keys[1], muscle_role=MuscleRole.PRIMARY, weighing=100))
            db.commit()
        with engine.connect() as connection:
            original = {
                name: connection.execute(text(f"SELECT * FROM {name}")).mappings().all()
                for name in ("app_user", "workout", "muscle_group", "muscle_workout")
            }
        migrate_database(engine, "muscle_workout@head")
        migrate_database(engine, "muscle_workout@head")
        with engine.connect() as connection:
            for name, rows in original.items():
                assert connection.execute(text(f"SELECT * FROM {name}")).mappings().all() == rows


@pytest.mark.parametrize("alteration", [
    "ALTER TABLE muscle_workout DROP CONSTRAINT chk_muscle_workout_weighing; ALTER TABLE muscle_workout ADD CONSTRAINT chk_muscle_workout_weighing CHECK (weighing > 0)",
    "ALTER TABLE muscle_workout DROP CONSTRAINT pk_muscle_workout; ALTER TABLE muscle_workout ADD CONSTRAINT pk_muscle_workout PRIMARY KEY (workout_id)",
])
def test_migration_rejects_incompatible_table_atomically(postgres_database_factory, alteration):
    with postgres_database_factory() as engine:
        for table in (AppUserModel.__table__, WorkoutModel.__table__, MuscleGroupModel.__table__, MuscleWorkoutModel.__table__):
            table.create(engine)
        with engine.begin() as connection:
            connection.execute(text(alteration))
        with pytest.raises(RuntimeError, match="incompatible"):
            migrate_database(engine, "muscle_workout@head")
        assert not inspect(engine).has_table("alembic_version")


def test_database_constraints_protect_direct_writes(postgres_catalog):
    db, keys = postgres_catalog
    controller.create_muscle_workout(db, payload(keys))
    for values, expected in (
        ({"workout": keys[0], "group": keys[1], "role": "PRIMARIO", "weight": 100}, "23505"),
        ({"workout": keys[0], "group": keys[1], "role": "SECUNDARIO", "weight": 100}, "23514"),
        ({"workout": 999999, "group": keys[1], "role": "PRIMARIO", "weight": 100}, "23503"),
        ({"workout": keys[0], "group": 999999, "role": "PRIMARIO", "weight": 100}, "23503"),
        ({"workout": keys[0], "group": keys[1], "role": "INVALID", "weight": 100}, "22P02"),
    ):
        with pytest.raises(DBAPIError) as error:
            with db.begin_nested():
                db.execute(text(
                    "INSERT INTO muscle_workout (workout_id, muscle_group_id, role_muscular, weighing) "
                    "VALUES (:workout, :group, :role, :weight)"
                ), values)
        assert error.value.orig.sqlstate == expected


def test_role_and_weighing_update_in_one_valid_statement(postgres_catalog):
    db, keys = postgres_catalog
    controller.create_muscle_workout(db, payload(keys))
    controller.update_muscle_workout(db, *keys, MuscleWorkoutUpdate(muscle_role=MuscleRole.SECONDARY))
    row = db.execute(text(
        "SELECT role_muscular::text, weighing FROM muscle_workout WHERE workout_id = :id"
    ), {"id": keys[0]}).one()
    assert tuple(row) == ("SECUNDARIO", 50)


@pytest.mark.parametrize("parent", ["workout", "muscle_group"])
def test_native_cascade_removes_only_links_and_deleted_parent(postgres_catalog, parent):
    db, keys = postgres_catalog
    controller.create_muscle_workout(db, payload(keys))
    identifier = keys[0] if parent == "workout" else keys[1]
    db.execute(text(f"DELETE FROM {parent} WHERE id = :id"), {"id": identifier})
    db.commit()
    remaining = "muscle_group" if parent == "workout" else "workout"
    assert db.execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 0
    assert db.execute(text(f"SELECT COUNT(*) FROM {remaining}")).scalar_one() == 1


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_history_rejections_preserve_association_and_sets(postgres_catalog, method):
    db, keys = postgres_catalog
    controller.create_muscle_workout(db, payload(keys))
    db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": keys[0]})
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            resource = f"/muscle-workouts/{keys[0]}/{keys[1]}"
            if method == "post":
                response = client.post("/muscle-workouts/", json=payload(keys).model_dump(mode="json"))
            elif method == "put":
                response = client.put(resource, json={"muscle_role": "TERCIARIO"})
            else:
                response = client.delete(resource)
            assert response.status_code == 409
            assert "recorded sets" in response.json()["detail"]
            assert client.get(resource).json()["weighing"] == 100
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert db.execute(text("SELECT COUNT(*) FROM workout_set")).scalar_one() == 1


@pytest.mark.parametrize("access", ["api", "database"])
def test_concurrent_duplicate_pairs_leave_one_link(postgres_database_factory, access):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_workout@head")
        with Session(engine) as db:
            keys = seed_catalog(db)
        barrier = Barrier(2)

        def override_get_db():
            with Session(engine) as db:
                yield db

        def create_concurrently(index):
            barrier.wait(timeout=10)
            if access == "api":
                with TestClient(app) as client:
                    return client.post("/muscle-workouts/", json=payload(keys).model_dump(mode="json")).status_code
            try:
                with engine.begin() as connection:
                    connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                    connection.execute(text(
                        "INSERT INTO muscle_workout VALUES (:workout, :group, 'PRIMARIO', 100)"
                    ), {"workout": keys[0], "group": keys[1]})
                return 201
            except DBAPIError as exc:
                assert exc.orig.sqlstate == "23505"
                return 409

        app.dependency_overrides[get_db] = override_get_db
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                assert sorted(executor.map(create_concurrently, range(2))) == [201, 409]
        finally:
            app.dependency_overrides.pop(get_db, None)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 1


def test_concurrent_first_set_is_seen_after_workout_lock(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_workout@head")
        create_series_table(engine)
        with Session(engine) as db:
            keys = seed_catalog(db)
        lock_attempted = Event()

        def observe_lock(connection, cursor, statement, parameters, context, executemany):
            if "FROM workout" in statement and "FOR UPDATE" in statement:
                lock_attempted.set()

        def override_get_db():
            with Session(engine) as db:
                yield db

        def create_association():
            with TestClient(app) as client:
                return client.post("/muscle-workouts/", json=payload(keys).model_dump(mode="json"))

        app.dependency_overrides[get_db] = override_get_db
        event.listen(engine, "before_cursor_execute", observe_lock)
        try:
            with engine.connect() as writer:
                transaction = writer.begin()
                writer.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": keys[0]})
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(create_association)
                    try:
                        assert lock_attempted.wait(timeout=10)
                    finally:
                        transaction.commit()
                    response = future.result(timeout=10)
                    assert response.status_code == 409
                    assert "recorded sets" in response.json()["detail"]
        finally:
            event.remove(engine, "before_cursor_execute", observe_lock)
            app.dependency_overrides.pop(get_db, None)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 0
