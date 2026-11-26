from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.controllers.audit_controller import (
    create_audit,
    get_audit,
    list_audits,
    record_audit_event,
)
from app.core.dependencies import AuditContext
from app.core.exceptions import (
    AuditDateRangeValidationException,
    AuditNotFoundException,
)
from app.models.audit_model import AuditAction, AuditModel
from app.schemas.audit_schema import AuditCreate


def make_audit_record(
    audit_id: int = 1,
    user_id: int | None = 1,
    entity: str = "workout_session",
    record_id: str = "42",
    action: AuditAction = AuditAction.INSERT,
    endpoint: str | None = "/workout-sessions/",
) -> AuditModel:
    return AuditModel(
        id=audit_id,
        user_id=user_id,
        entity=entity,
        record_id=record_id,
        action=action,
        endpoint=endpoint,
        created_at=datetime(2026, 11, 21, 10, 0, 0),
    )


def test_create_audit_commits_when_user_exists():
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)
    payload = AuditCreate(
        user_id=1,
        entity="workout_session",
        record_id="42",
        action=AuditAction.INSERT,
        endpoint="/workout-sessions/",
    )

    result = create_audit(db, payload)

    db.execute.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)
    assert result.user_id == 1
    assert result.action == AuditAction.INSERT


def test_create_audit_allows_null_user_id_without_user_lookup():
    db = MagicMock()
    payload = AuditCreate(
        user_id=None,
        entity="workout_session",
        record_id="42",
        action=AuditAction.EXPORT,
        endpoint="/exports/sessions",
    )

    result = create_audit(db, payload)

    db.execute.assert_not_called()
    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert result.user_id is None
    assert result.action == AuditAction.EXPORT


def test_create_audit_raises_404_when_user_missing():
    db = MagicMock()
    db.execute.return_value.first.return_value = None
    payload = AuditCreate(
        user_id=999,
        entity="app_user",
        record_id="999",
        action=AuditAction.UPDATE,
    )

    with pytest.raises(HTTPException) as exc:
        create_audit(db, payload)

    assert exc.value.status_code == 404
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_audit_rolls_back_on_commit_error():
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = RuntimeError("db error")
    payload = AuditCreate(
        user_id=1,
        entity="workout",
        record_id="7",
        action=AuditAction.DELETE,
    )

    with pytest.raises(RuntimeError):
        create_audit(db, payload)

    db.rollback.assert_called_once()


def test_record_audit_event_helper_flushes_without_commit():
    db = MagicMock()
    context = AuditContext(user_id=1, endpoint="DELETE /app-users/1")

    result = record_audit_event(
        db,
        entity="app_user",
        record_id=1,
        action="DELETE",
        context=context,
    )

    assert result.user_id == 1
    assert result.entity == "app_user"
    assert result.record_id == "1"
    assert result.action == AuditAction.DELETE
    assert result.endpoint == "DELETE /app-users/1"
    db.add.assert_called_once_with(result)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_record_audit_event_helper_allows_anonymous_context():
    db = MagicMock()
    context = AuditContext(user_id=None, endpoint="DELETE /app-users/5")

    result = record_audit_event(
        db,
        "app_user",
        "5",
        AuditAction.DELETE,
        context,
    )

    assert result.user_id is None
    assert result.entity == "app_user"
    assert result.record_id == "5"
    assert result.action == AuditAction.DELETE
    assert result.endpoint == "DELETE /app-users/5"
    db.add.assert_called_once_with(result)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_list_audits_applies_order_and_pagination():
    db = MagicMock()
    query = db.query.return_value
    query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        make_audit_record()
    ]

    result = list_audits(db, skip=10, limit=25)

    assert len(result) == 1
    assert result[0].id == 1
    query.filter.assert_not_called()
    query.order_by.return_value.offset.assert_called_once_with(10)
    query.order_by.return_value.offset.return_value.limit.assert_called_once_with(25)


def test_list_audits_applies_all_filters():
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        make_audit_record(action=AuditAction.UPDATE)
    ]

    result = list_audits(
        db,
        user_id=1,
        entity="workout_session",
        record_id="42",
        action=AuditAction.UPDATE,
        date_from=datetime(2026, 11, 20, 0, 0, 0),
        date_to=datetime(2026, 11, 21, 23, 59, 59),
    )

    assert len(result) == 1
    assert query.filter.call_count == 6


def test_list_audits_rejects_inverted_date_range():
    db = MagicMock()

    with pytest.raises(AuditDateRangeValidationException) as exc:
        list_audits(
            db,
            date_from=datetime(2026, 11, 22, 0, 0, 0),
            date_to=datetime(2026, 11, 20, 0, 0, 0),
        )

    assert exc.value.status_code == 400
    db.query.assert_not_called()


def test_get_audit_returns_record():
    db = MagicMock()
    record = make_audit_record(audit_id=5)
    db.query.return_value.filter.return_value.first.return_value = record

    result = get_audit(db, 5)

    assert result.id == 5


def test_get_audit_raises_404_when_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(AuditNotFoundException) as exc:
        get_audit(db, 999)

    assert exc.value.status_code == 404
