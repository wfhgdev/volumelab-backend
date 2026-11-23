from contextlib import contextmanager
from pathlib import Path
import re
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text

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
