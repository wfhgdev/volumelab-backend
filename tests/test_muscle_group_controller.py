from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import DBAPIError

from app.controllers import muscle_group_controller as controller
from app.models.app_user_model import AppUserModel
from app.models.muscle_group_model import MuscleGroupModel
from app.schemas.muscle_group_schema import MuscleGroupCreate, MuscleGroupUpdate


class DatabaseError(Exception):
    def __init__(self, sqlstate, diag=None):
        super().__init__("Private database details")
        self.sqlstate = sqlstate
        self.diag = diag


def make_record():
    return MuscleGroupModel(id=1, name="Chest", description="Original", created_by=1)


def make_database(record=None, role="ADMIN", creator_exists=True):
    db = MagicMock()
    groups = MagicMock()
    users = MagicMock()
    for query in (groups, users):
        query.filter.return_value = query
        query.with_for_update.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
    groups.first.return_value = record
    users.first.return_value = AppUserModel(id=1, role=role) if creator_exists else None
    db.query.side_effect = lambda model: users if model is AppUserModel else groups
    return db, groups, users


def test_creation_by_administrator_commits():
    db, _, users = make_database()
    result = controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=1))
    assert result.name == "Chest"
    users.with_for_update.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)


@pytest.mark.parametrize(("role", "exists", "status"), [
    ("CLIENTE", True, 403), ("ADMIN", False, 404),
])
def test_creation_validates_administrator(role, exists, status):
    db, _, _ = make_database(role=role, creator_exists=exists)
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=1))
    assert error.value.status_code == status
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_creation_rejects_duplicate_name():
    db, _, _ = make_database(make_record())
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=1))
    assert error.value.status_code == 409


@pytest.mark.parametrize("operation", [
    lambda db: controller.get_muscle_group(db, 99),
    lambda db: controller.update_muscle_group(db, 99, MuscleGroupUpdate(name="Back")),
    lambda db: controller.delete_muscle_group(db, 99),
])
def test_missing_record_returns_not_found(operation):
    db, _, _ = make_database()
    with pytest.raises(HTTPException) as error:
        operation(db)
    assert error.value.status_code == 404


def test_partial_update_preserves_omitted_fields():
    db, _, _ = make_database(make_record())
    result = controller.update_muscle_group(db, 1, MuscleGroupUpdate(description=None))
    assert result.description is None
    assert result.name == "Chest"
    assert result.created_by == 1
    db.commit.assert_called_once()


def test_update_rejects_non_administrator_creator():
    db, _, _ = make_database(make_record(), role="CLIENTE")
    with pytest.raises(HTTPException) as error:
        controller.update_muscle_group(db, 1, MuscleGroupUpdate(created_by=2))
    assert error.value.status_code == 403
    db.commit.assert_not_called()


def test_list_applies_creator_filter_and_pagination():
    record = make_record()
    db, groups, _ = make_database(record)
    groups.all.return_value = [record]
    assert controller.list_muscle_groups(db, 2, 5, 1) == [record]
    groups.offset.assert_called_once_with(2)
    groups.limit.assert_called_once_with(5)
    groups.filter.assert_called_once()


@pytest.mark.parametrize("associated", [False, True])
def test_deletion_preserves_associated_groups(monkeypatch, associated):
    db, groups, _ = make_database(make_record())
    inspector = MagicMock()
    inspector.has_table.return_value = True
    monkeypatch.setattr(controller, "inspect", lambda bind: inspector)
    db.execute.return_value.first.return_value = (1,) if associated else None
    if associated:
        with pytest.raises(HTTPException) as error:
            controller.delete_muscle_group(db, 1)
        assert error.value.status_code == 409
        db.delete.assert_not_called()
        db.commit.assert_not_called()
    else:
        controller.delete_muscle_group(db, 1)
        db.delete.assert_called_once_with(groups.first.return_value)
        db.commit.assert_called_once()
    groups.with_for_update.assert_called_once()


def test_deletion_supports_schema_without_association_table(monkeypatch):
    db, _, _ = make_database(make_record())
    inspector = MagicMock()
    inspector.has_table.return_value = False
    monkeypatch.setattr(controller, "inspect", lambda bind: inspector)
    controller.delete_muscle_group(db, 1)
    db.execute.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize(("sqlstate", "status"), [
    ("23505", 409), ("23503", 409), ("23001", 409), ("23502", 422),
    ("23514", 422), ("22P02", 422), ("08006", 500),
])
def test_database_errors_are_rolled_back_and_sanitized(sqlstate, status):
    db, _, _ = make_database()
    db.commit.side_effect = DBAPIError("Private SQL", {}, DatabaseError(sqlstate))
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=1))
    assert error.value.status_code == status
    assert "Private" not in error.value.detail
    db.rollback.assert_called_once()


@pytest.mark.parametrize("diagnostic", [
    SimpleNamespace(constraint_name="muscle_group_admin_only", context=None),
    SimpleNamespace(constraint_name=None, context="PL/pgSQL function fn_muscle_group_admin_only()"),
])
def test_existing_and_new_trigger_errors_return_forbidden(diagnostic):
    db, _, _ = make_database()
    db.commit.side_effect = DBAPIError("INSERT", {}, DatabaseError("P0001", diagnostic))
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_group(db, MuscleGroupCreate(name="Chest", created_by=1))
    assert error.value.status_code == 403


def test_read_errors_are_sanitized():
    db = MagicMock()
    db.query.side_effect = DBAPIError("Private SQL", {}, DatabaseError("08006"))
    with pytest.raises(HTTPException) as error:
        controller.list_muscle_groups(db)
    assert error.value.status_code == 500
    db.rollback.assert_called_once()
