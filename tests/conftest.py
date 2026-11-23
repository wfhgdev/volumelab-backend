import pytest
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database_connection import SessionLocal, engine, get_db
from app.models.app_user_model import AppUserModel
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.main import app


engine.echo = False


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

