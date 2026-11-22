import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database_connection import Base, get_db
from app.models.app_user_model import AppUserModel
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.training_week_model import TrainingWeekModel
from app.main import app


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
    """Crea una base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


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
        email="test_user@volumelab.com",
        password_hash="hashed_secret_password",
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
def muscle_group_api(client, db_session, test_user):
    test_user.role = "ADMIN"
    db_session.commit()
    db_session.execute(text(
        "CREATE TABLE muscle_workout (workout_id INTEGER NOT NULL, "
        "muscle_group_id INTEGER NOT NULL REFERENCES muscle_group(id) ON DELETE CASCADE, "
        "PRIMARY KEY (workout_id, muscle_group_id))"
    ))
    db_session.commit()
    try:
        yield client, db_session, test_user
    finally:
        db_session.rollback()
        db_session.execute(text("DROP TABLE IF EXISTS muscle_workout"))
        db_session.commit()

