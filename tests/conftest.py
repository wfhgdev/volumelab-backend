import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-1234567890-test-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

from datetime import date
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database_connection import SessionLocal, engine, get_db
from app.core.security import create_access_token, hash_password
from app.models.app_user_model import AppUserModel
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.muscle_group_model import MuscleGroupModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_model import ExerciseType, WorkoutModel
from app.main import app

engine.echo = False

pytest_plugins = ("tests.postgres_fixtures",)

# Base de datos en memoria para pruebas aisladas
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    """Sesión PostgreSQL real con rollback al final de cada test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        finally:
            connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP de pruebas con get_db sobreescrito."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session) -> AppUserModel:
    """Crea un usuario de prueba en la base de datos."""
    user = AppUserModel(
        email=f"test_user_{uuid4().hex}@volumelab.com",
        password_hash=hash_password("hashed_secret_password"),
        name="Beatriz",
        lastname="Iñiguez",
        role="CLIENTE",
        status="ACTIVO"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session) -> AppUserModel:
    """Crea un administrador de prueba en la base de datos."""
    user = AppUserModel(
        email=f"admin_user_{uuid4().hex}@volumelab.com",
        password_hash=hash_password("Admin1234!"),
        name="Administrador",
        lastname="VolumeLab",
        role="ADMIN",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client_user(db_session) -> AppUserModel:
    """Crea un cliente autenticado de prueba."""
    user = AppUserModel(
        email=f"client_user_{uuid4().hex}@volumelab.com",
        password_hash=hash_password("Client1234!"),
        name="Carlos",
        lastname="Cliente",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def other_client_user(db_session) -> AppUserModel:
    """Crea un segundo cliente autenticado de prueba."""
    user = AppUserModel(
        email=f"other_client_{uuid4().hex}@volumelab.com",
        password_hash=hash_password("Client1234!"),
        name="Diana",
        lastname="Otro",
        role="CLIENTE",
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_auth_headers(user: AppUserModel) -> dict[str, str]:
    token = create_access_token(user_id=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_client(client, admin_user):
    client.headers.update(create_auth_headers(admin_user))
    return client


@pytest.fixture(scope="function")
def user_client(client, client_user):
    client.headers.update(create_auth_headers(client_user))
    return client


@pytest.fixture(scope="function")
def test_mesocycle(db_session, test_user) -> MesocycleModel:
    """Crea un mesociclo de prueba en la base de datos."""
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


@pytest.fixture
def workout_db(db_session):
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
