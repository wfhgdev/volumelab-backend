import os
from contextlib import contextmanager
from datetime import date
from uuid import uuid4

TEST_DATABASE_NAME = os.environ.setdefault(
    "VOLUMELAB_TEST_DATABASE_NAME", f"volumelab_test_{uuid4().hex[:12]}"
)
os.environ.update(
    SECRET_KEY="test-secret-key-1234567890-test-only",
    ALGORITHM="HS256",
    ACCESS_TOKEN_EXPIRE_MINUTES="60",
    DB_NAME=TEST_DATABASE_NAME,
    DB_ECHO="false",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database_connection import engine as application_engine, get_db
from app.core.security import create_access_token, hash_password
from app.models.app_user_model import AppUserModel
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.muscle_group_model import MuscleGroupModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_model import ExerciseType, WorkoutModel
from app.main import app

pytest_plugins = ("tests.postgres_fixtures",)


@pytest.fixture(scope="session")
def test_engine(database_factory):
    from tests.postgres_fixtures import install_rating_triggers, migrate_database

    with database_factory(TEST_DATABASE_NAME) as engine:
        migrate_database(engine, "heads")
        install_rating_triggers(engine)
        try:
            yield engine
        finally:
            application_engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        finally:
            connection.close()


@pytest.fixture
def client_factory(db_session):
    def override_get_db():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    @contextmanager
    def create_client(user=None):
        headers = create_auth_headers(user) if user is not None else {}
        with TestClient(app, headers=headers) as test_client:
            yield test_client

    try:
        yield create_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def client(client_factory):
    with client_factory() as test_client:
        yield test_client


@pytest.fixture
def user_factory(db_session):
    def create_user(*, role="CLIENTE", status="ACTIVO", password="Client1234!", **fields):
        user = AppUserModel(
            email=fields.pop("email", f"user_{uuid4().hex}@example.com"),
            name=fields.pop("name", "Test user"),
            password_hash=hash_password(password),
            role=role,
            status=status,
            **fields,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return create_user


@pytest.fixture(scope="function")
def test_user(user_factory) -> AppUserModel:
    return user_factory(name="Test member", password="hashed_secret_password")


@pytest.fixture(scope="function")
def admin_user(user_factory) -> AppUserModel:
    return user_factory(role="ADMIN", name="Administrator", password="Admin1234!")


@pytest.fixture(scope="function")
def client_user(user_factory) -> AppUserModel:
    return user_factory(name="Client")


@pytest.fixture(scope="function")
def other_client_user(user_factory) -> AppUserModel:
    return user_factory(name="Other client")


def create_auth_headers(user: AppUserModel) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_client(client_factory, admin_user):
    with client_factory(admin_user) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def user_client(client_factory, client_user):
    with client_factory(client_user) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def test_mesocycle(db_session, test_user) -> MesocycleModel:
    meso = MesocycleModel(
        user_id=test_user.id,
        name="Mesociclo Base",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status=MesocycleStatus.PLANIFICADO
    )
    db_session.add(meso)
    db_session.commit()
    db_session.refresh(meso)
    return meso


def _clear_catalog_tables(db_session) -> None:
    db_session.execute(
        text(
            "TRUNCATE TABLE public.workout_set, public.workout_rate, "
            "public.muscle_workout, public.workout, public.muscle_group CASCADE"
        )
    )
    db_session.flush()


@pytest.fixture
def workout_db(db_session):
    _clear_catalog_tables(db_session)
    db_session.execute(text(
        "CREATE TEMP TABLE IF NOT EXISTS workout_set ("
        "id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, "
        "exercise_id INTEGER NOT NULL)"
    ))
    db_session.commit()
    try:
        yield db_session
    finally:
        db_session.rollback()
        db_session.execute(text("DROP TABLE IF EXISTS pg_temp.workout_set"))
        db_session.commit()


@pytest.fixture
def workout_api(client, workout_db, test_user):
    client.headers.update(create_auth_headers(test_user))
    return client, workout_db, test_user


@pytest.fixture
def muscle_group_api(client, db_session, test_user):
    _clear_catalog_tables(db_session)
    test_user.role = "ADMIN"
    db_session.commit()
    client.headers.update(create_auth_headers(test_user))
    return client, db_session, test_user


@pytest.fixture
def association_api(client, workout_db, test_user):
    test_user.role = "ADMIN"
    client.headers.update(create_auth_headers(test_user))
    workout = WorkoutModel(name="Squat", type=ExerciseType.DYNAMIC, created_by=test_user.id)
    group = MuscleGroupModel(name="Legs", created_by=test_user.id)
    workout_db.add_all([workout, group])
    workout_db.commit()
    return client, workout_db, workout, group
