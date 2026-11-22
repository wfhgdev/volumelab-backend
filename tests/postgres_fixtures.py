from contextlib import contextmanager
from pathlib import Path
import re
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings


def pytest_addoption(parser):
    parser.addoption("--run-postgres", action="store_true", default=False)


def migrate_database(engine, target, downgrade=False):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        operation = command.downgrade if downgrade else command.upgrade
        operation(config, target)


@pytest.fixture(scope="session")
def postgres_database_factory(request):
    if not request.config.getoption("--run-postgres"):
        pytest.skip("Use --run-postgres to run isolated PostgreSQL tests")
    source = create_engine(settings.database_url)
    admin = create_engine(source.url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    source.dispose()

    @contextmanager
    def isolated_database():
        database_name = f"volumelab_test_{uuid4().hex[:12]}"
        if not re.fullmatch(r"volumelab_test_[0-9a-f]{12}", database_name):
            raise ValueError("Invalid isolated database name")
        quoted_name = admin.dialect.identifier_preparer.quote(database_name)
        with admin.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {quoted_name}"))
        engine = create_engine(admin.url.set(database=database_name), isolation_level="READ COMMITTED")
        try:
            yield engine
        finally:
            engine.dispose()
            with admin.connect() as connection:
                connection.execute(text(f"DROP DATABASE {quoted_name} WITH (FORCE)"))

    try:
        yield isolated_database
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def workout_postgres_engine(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "workout@head")
        migrate_database(engine, "e7b92c431d01")
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE workout_set (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
                "exercise_id integer NOT NULL REFERENCES workout(id) ON DELETE RESTRICT)"
            ))
            connection.execute(text("""
                CREATE FUNCTION fn_test_workout_rate_visibility() RETURNS trigger AS $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM workout WHERE id = NEW.id_workout AND public AND state) THEN
                        RAISE EXCEPTION 'The workout must be public and active';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER trg_test_workout_rate_visibility BEFORE INSERT OR UPDATE ON workout_rate
                FOR EACH ROW EXECUTE FUNCTION fn_test_workout_rate_visibility()
            """))
        yield engine


@pytest.fixture
def postgres_db(workout_postgres_engine):
    with workout_postgres_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            try:
                yield session
            finally:
                session.close()
                transaction.rollback()
