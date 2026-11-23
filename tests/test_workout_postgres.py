from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.controllers.workout_controller import create_workout, delete_workout, update_workout
from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.workout_schema import WorkoutCreate, WorkoutUpdate
from tests.postgres_fixtures import migrate_database

pytestmark = pytest.mark.postgres


def add_user(db, role="CLIENTE"):
    user = AppUserModel(name="Test user", email=f"{role.lower()}@example.com", password_hash="test", role=role,
                        status="ACTIVO")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def postgres_user(postgres_db):
    return add_user(postgres_db)


def test_migration_creates_and_reverses_workout_schema(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine)
        inspector = inspect(engine)
        assert inspector.has_table("workout")
        assert len(inspector.get_columns("workout")) == 10
        assert inspector.get_columns("workout")[0]["identity"]["always"] is True
        assert "uq_workout_name" in {constraint["name"] for constraint in inspector.get_unique_constraints("workout")}
        migrate_database(engine, "ad8c21f5e9b7", downgrade=True)
        assert not inspect(engine).has_table("workout")
        migrate_database(engine)
        assert inspect(engine).has_table("workout")


def test_migration_adopts_unversioned_table_without_losing_data(postgres_database_factory):
    with postgres_database_factory() as engine:
        AppUserModel.__table__.create(engine)
        WorkoutModel.__table__.create(engine)
        with Session(engine) as db:
            user = add_user(db)
            db.add(WorkoutModel(name="Existing exercise", type=ExerciseType.DYNAMIC, created_by=user.id))
            db.commit()
        with engine.connect() as connection:
            before = connection.execute(text("SELECT * FROM workout")).mappings().all()
        migrate_database(engine)
        migrate_database(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT * FROM workout")).mappings().all() == before
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "f2a7c8e9d410"


def test_migration_rejects_incompatible_existing_schema(postgres_database_factory):
    with postgres_database_factory() as engine:
        AppUserModel.__table__.create(engine)
        WorkoutModel.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE workout ALTER COLUMN name TYPE varchar(100)"))
        with pytest.raises(RuntimeError, match="length of 200"):
            migrate_database(engine)
        assert inspect(engine).get_columns("workout")[1]["type"].length == 100


@pytest.mark.parametrize("disable_trigger", [False, True])
def test_adoption_validates_and_preserves_existing_trigger(postgres_database_factory, disable_trigger):
    with postgres_database_factory() as engine:
        migrate_database(engine)
        with engine.begin() as connection:
            original = connection.execute(text("SELECT pg_get_functiondef('fn_workout_client_limit()'::regprocedure)")).scalar_one()
            connection.execute(text("UPDATE alembic_version SET version_num = 'ad8c21f5e9b7'"))
            if disable_trigger:
                connection.execute(text("ALTER TABLE workout DISABLE TRIGGER trg_workout_client_limit"))
        if disable_trigger:
            with pytest.raises(RuntimeError, match="trigger is incompatible"):
                migrate_database(engine)
        else:
            migrate_database(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT pg_get_functiondef('fn_workout_client_limit()'::regprocedure)")).scalar_one() == original


def test_database_constraints_protect_direct_writes(postgres_db, postgres_user):
    record = create_workout(postgres_db, WorkoutCreate(name="Squat", type=ExerciseType.DYNAMIC, created_by=postgres_user.id))
    cases = [
        ({"name": record.name, "type": "DINAMICO", "created_by": postgres_user.id}, "23505"),
        ({"name": "Invalid ballast", "type": "DINAMICO", "created_by": postgres_user.id,
          "allow_negative_ballast": True}, "23514"),
        ({"name": "Missing creator", "type": "DINAMICO", "created_by": None}, "23502"),
        ({"name": "Unknown creator", "type": "DINAMICO", "created_by": 999999}, "23503"),
    ]
    for values, sqlstate in cases:
        with pytest.raises(DBAPIError) as error:
            with postgres_db.begin_nested():
                postgres_db.add(WorkoutModel(**values))
                postgres_db.flush()
        assert error.value.orig.sqlstate == sqlstate


def test_trigger_rejects_creation_and_publication_beyond_limit(postgres_db, postgres_user):
    postgres_db.add_all(
        [WorkoutModel(name=f"Public {index}", type=ExerciseType.DYNAMIC, created_by=postgres_user.id, public=True, state=False)
         for index in range(20)])
    postgres_db.commit()
    for operation in ("insert", "publish"):
        private = WorkoutModel(name=f"Private {operation}", type=ExerciseType.DYNAMIC, created_by=postgres_user.id)
        if operation == "publish":
            postgres_db.add(private)
            postgres_db.commit()
        with pytest.raises(DBAPIError) as error:
            with postgres_db.begin_nested():
                private.public = True
                postgres_db.add(private)
                postgres_db.flush()
        assert error.value.orig.sqlstate == "P0001"
        assert error.value.orig.diag.constraint_name == "workout_public_limit"


def test_creator_deletion_anonymizes_and_keeps_recorded_sets(postgres_db, postgres_user):
    record = create_workout(postgres_db, WorkoutCreate(name="Squat", type=ExerciseType.DYNAMIC, created_by=postgres_user.id))
    postgres_db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": record.id})
    postgres_db.commit()
    postgres_db.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": postgres_user.id})
    postgres_db.commit()
    postgres_db.refresh(record)
    assert record.created_by is None
    delete_workout(postgres_db, record.id)
    assert postgres_db.execute(text("SELECT COUNT(*) FROM workout_set WHERE exercise_id = :id"),
                               {"id": record.id}).scalar_one() == 1
    assert update_workout(postgres_db, record.id, WorkoutUpdate(description="Preserved")).description == "Preserved"


def test_physical_deletion_is_restricted_when_sets_exist(postgres_db, postgres_user):
    record = create_workout(postgres_db, WorkoutCreate(name="Squat", type=ExerciseType.DYNAMIC, created_by=postgres_user.id))
    postgres_db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": record.id})
    postgres_db.commit()
    with pytest.raises(DBAPIError) as error:
        with postgres_db.begin_nested():
            postgres_db.execute(text("DELETE FROM workout WHERE id = :id"), {"id": record.id})
    assert error.value.orig.sqlstate in {"23001", "23503"}


@pytest.mark.parametrize("access", ["api", "database"])
def test_concurrent_public_creation_never_exceeds_twenty(postgres_database_factory, access):
    with postgres_database_factory() as engine:
        migrate_database(engine)
        with Session(engine) as db:
            user = add_user(db)
            user_id = user.id
            db.add_all(
                [WorkoutModel(name=f"Existing {index}", type=ExerciseType.DYNAMIC, created_by=user_id, public=True) for index in
                 range(19)])
            db.commit()
        barrier = Barrier(2)

        def override_get_db():
            with Session(engine) as session:
                yield session

        def create_concurrently(index):
            barrier.wait(timeout=10)
            if access == "api":
                with TestClient(app) as client:
                    return client.post("/workouts/",
                                       json={"name": f"Concurrent {index}", "type": "DINAMICO", "created_by": user_id,
                                             "public": True}).status_code
            try:
                with engine.begin() as connection:
                    connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                    connection.execute(text(
                        "INSERT INTO workout (name, type, created_by, public) VALUES (:name, 'DINAMICO', :user_id, true)"),
                                       {"name": f"Concurrent {index}", "user_id": user_id})
                return 201
            except DBAPIError as exc:
                assert exc.orig.sqlstate == "P0001"
                return 409

        app.dependency_overrides[get_db] = override_get_db
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                assert sorted(executor.map(create_concurrently, range(2))) == [201, 409]
        finally:
            app.dependency_overrides.pop(get_db, None)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM workout WHERE public")).scalar_one() == 20
