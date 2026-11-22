from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.controllers import muscle_group_controller as controller
from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.muscle_group_model import MuscleGroupModel
from app.schemas.muscle_group_schema import MuscleGroupCreate, MuscleGroupUpdate
from tests.postgres_fixtures import migrate_database
from tests.catalog_support import associate_group


pytestmark = pytest.mark.postgres


def add_user(db, role="ADMIN", email=None):
    user = AppUserModel(
        name="Test creator", email=email or f"{role.lower()}@example.com",
        password_hash="test", role=role, status="ACTIVO",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture(scope="module")
def group_engine(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_workout@head")
        yield engine


@pytest.fixture
def group_db(group_engine):
    with group_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as db:
            try:
                yield db
            finally:
                db.close()
                transaction.rollback()


def test_migration_creates_and_reverses_group_schema(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_group@head")
        columns = inspect(engine).get_columns("muscle_group")
        assert {column["name"] for column in columns} == {"id", "name", "description", "created_by"}
        assert columns[0]["identity"]["always"] is True
        migrate_database(engine, "ad8c21f5e9b7", downgrade=True)
        assert not inspect(engine).has_table("muscle_group")
        migrate_database(engine, "muscle_group@head")
        assert inspect(engine).has_table("muscle_group")


def test_migration_adopts_unversioned_table_without_losing_data(postgres_database_factory):
    with postgres_database_factory() as engine:
        AppUserModel.__table__.create(engine)
        MuscleGroupModel.__table__.create(engine)
        with Session(engine) as db:
            admin = add_user(db)
            db.add(MuscleGroupModel(name="Existing group", created_by=admin.id))
            db.commit()
        with engine.connect() as connection:
            original = connection.execute(text("SELECT * FROM muscle_group")).mappings().all()
        migrate_database(engine, "muscle_group@head")
        migrate_database(engine, "muscle_group@head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT * FROM muscle_group")).mappings().all() == original
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "d3c8a51f9072"


@pytest.mark.parametrize("alteration", [
    "ALTER TABLE muscle_group ALTER COLUMN name TYPE varchar(80)",
    "ALTER TABLE muscle_group ALTER COLUMN description SET NOT NULL",
])
def test_migration_rejects_incompatible_schema_atomically(postgres_database_factory, alteration):
    with postgres_database_factory() as engine:
        AppUserModel.__table__.create(engine)
        MuscleGroupModel.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(text(alteration))
        with pytest.raises(RuntimeError, match="incompatible|length of 150"):
            migrate_database(engine, "muscle_group@head")
        assert not inspect(engine).has_table("alembic_version")


@pytest.mark.parametrize("disabled", [False, True])
def test_adoption_validates_and_preserves_existing_trigger(postgres_database_factory, disabled):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_group@head")
        with engine.begin() as connection:
            original = connection.execute(text(
                "SELECT pg_get_functiondef('fn_muscle_group_admin_only()'::regprocedure)"
            )).scalar_one()
            connection.execute(text("UPDATE alembic_version SET version_num = 'ad8c21f5e9b7'"))
            if disabled:
                connection.execute(text("ALTER TABLE muscle_group DISABLE TRIGGER trg_muscle_group_admin_only"))
        if disabled:
            with pytest.raises(RuntimeError, match="trigger is incompatible"):
                migrate_database(engine, "muscle_group@head")
        else:
            migrate_database(engine, "muscle_group@head")
        with engine.connect() as connection:
            assert connection.execute(text(
                "SELECT pg_get_functiondef('fn_muscle_group_admin_only()'::regprocedure)"
            )).scalar_one() == original


def test_controller_lifecycle_in_postgres(group_db):
    admin = add_user(group_db)
    record = controller.create_muscle_group(group_db, MuscleGroupCreate(name="Chest", created_by=admin.id))
    assert record.id > 0
    assert controller.get_muscle_group(group_db, record.id).name == "Chest"
    updated = controller.update_muscle_group(group_db, record.id, MuscleGroupUpdate(description="Pectorals"))
    assert updated.description == "Pectorals"
    controller.delete_muscle_group(group_db, record.id)
    with pytest.raises(HTTPException) as error:
        controller.get_muscle_group(group_db, record.id)
    assert error.value.status_code == 404


def test_trigger_protects_direct_creation_and_reassignment(group_db):
    admin = add_user(group_db)
    client = add_user(group_db, role="CLIENTE")
    cases = [(client.id, "P0001"), (None, "23502"), (999999, "P0001")]
    for creator_id, expected in cases:
        with pytest.raises(DBAPIError) as error:
            with group_db.begin_nested():
                group_db.execute(text(
                    "INSERT INTO muscle_group (name, created_by) VALUES ('Invalid group', :creator)"
                ), {"creator": creator_id})
        assert error.value.orig.sqlstate == expected
    record = controller.create_muscle_group(group_db, MuscleGroupCreate(name="Chest", created_by=admin.id))
    with pytest.raises(DBAPIError) as error:
        with group_db.begin_nested():
            group_db.execute(text(
                "UPDATE muscle_group SET created_by = :creator WHERE id = :id"
            ), {"creator": client.id, "id": record.id})
    assert error.value.orig.diag.constraint_name == "muscle_group_admin_only"


def test_unique_constraint_protects_direct_writes(group_db):
    admin = add_user(group_db)
    controller.create_muscle_group(group_db, MuscleGroupCreate(name="Chest", created_by=admin.id))
    with pytest.raises(DBAPIError) as error:
        with group_db.begin_nested():
            group_db.execute(text(
                "INSERT INTO muscle_group (name, created_by) VALUES ('Chest', :creator)"
            ), {"creator": admin.id})
    assert error.value.orig.sqlstate == "23505"


def test_association_protection_and_creator_anonymization(group_db):
    admin = add_user(group_db)
    record = controller.create_muscle_group(group_db, MuscleGroupCreate(name="Chest", created_by=admin.id))
    associate_group(group_db, record.id, admin.id, count=2)
    with pytest.raises(HTTPException) as error:
        controller.delete_muscle_group(group_db, record.id)
    assert error.value.status_code == 409
    group_db.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": admin.id})
    group_db.commit()
    group_db.refresh(record)
    assert record.created_by is None
    assert group_db.execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 2
    assert controller.update_muscle_group(group_db, record.id, MuscleGroupUpdate(description="Preserved")).description == "Preserved"


def test_deletion_works_with_only_this_migration(postgres_database_factory):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_group@head")
        with Session(engine) as db:
            admin = add_user(db)
            record = controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=admin.id))
            record_id = record.id
            controller.delete_muscle_group(db, record_id)
            assert db.get(MuscleGroupModel, record_id) is None


@pytest.mark.parametrize("access", ["api", "database"])
def test_concurrent_duplicate_names_preserve_uniqueness(postgres_database_factory, access):
    with postgres_database_factory() as engine:
        migrate_database(engine, "muscle_group@head")
        with Session(engine) as db:
            creators = [add_user(db, email=f"admin{index}@example.com").id for index in range(2)]
        barrier = Barrier(2)

        def override_get_db():
            with Session(engine) as db:
                yield db

        def create_concurrently(index):
            barrier.wait(timeout=10)
            if access == "api":
                with TestClient(app) as client:
                    return client.post("/muscle-groups/", json={
                        "name": "Chest", "created_by": creators[index],
                    }).status_code
            try:
                with engine.begin() as connection:
                    connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                    connection.execute(text(
                        "INSERT INTO muscle_group (name, created_by) VALUES ('Chest', :creator)"
                    ), {"creator": creators[index]})
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
            assert connection.execute(text("SELECT COUNT(*) FROM muscle_group")).scalar_one() == 1
