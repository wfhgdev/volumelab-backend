from datetime import datetime
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.controllers.audit_controller import (
    create_audit,
    delete_audit,
    get_audit,
    list_audits,
    record_audit_event,
    update_audit,
)
from app.core.audit_logger import AuditLogLevel
from app.core.exceptions import (
    AuditDateRangeValidationException,
    AuditNotFoundException,
)
from app.models.audit_model import AuditAction, AuditModel
from app.schemas.audit_schema import AuditCreate, AuditUpdate


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


def test_create_audit_commits_and_logs_info_when_user_exists(caplog):
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)
    payload = AuditCreate(
        user_id=1,
        entity="workout_session",
        record_id="42",
        action=AuditAction.INSERT,
        endpoint="/workout-sessions/",
    )

    with caplog.at_level(logging.INFO, logger="volumelab.audit"):
        result = create_audit(db, payload)

    db.execute.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)
    assert result.user_id == 1
    assert result.action == AuditAction.INSERT
    assert any(r.levelno == logging.INFO for r in caplog.records)


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


def test_create_audit_raises_404_and_logs_warning_when_user_missing(caplog):
    db = MagicMock()
    db.execute.return_value.first.return_value = None
    payload = AuditCreate(
        user_id=999,
        entity="app_user",
        record_id="999",
        action=AuditAction.UPDATE,
    )

    with caplog.at_level(logging.WARNING, logger="volumelab.audit"):
        with pytest.raises(HTTPException) as exc:
            create_audit(db, payload)

    assert exc.value.status_code == 404
    db.add.assert_not_called()
    db.commit.assert_not_called()
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_create_audit_rolls_back_and_logs_error_on_commit_error(caplog):
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = RuntimeError("db error")
    payload = AuditCreate(
        user_id=1,
        entity="workout",
        record_id="7",
        action=AuditAction.DELETE,
    )

    with caplog.at_level(logging.ERROR, logger="volumelab.audit"):
        with pytest.raises(RuntimeError):
            create_audit(db, payload)

    db.rollback.assert_called_once()
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_record_audit_event_helper_persists_and_logs_critical(caplog):
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)

    with caplog.at_level(logging.INFO, logger="volumelab.audit"):
        result = record_audit_event(
            db,
            user_id=1,
            entity="app_user",
            record_id=1,
            action=AuditAction.DELETE,
            endpoint="/app-users/1",
            level=AuditLogLevel.CRITICAL,
            message="Incidencia en borrado RGPD art. 17",
            details={"reason": "timeout"},
        )

    assert result.record_id == "1"
    assert result.action == AuditAction.DELETE
    db.commit.assert_called_once()
    assert any(r.levelno == logging.CRITICAL for r in caplog.records)


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


def test_list_audits_rejects_inverted_date_range_and_logs_warning(caplog):
    db = MagicMock()

    with caplog.at_level(logging.WARNING, logger="volumelab.audit"):
        with pytest.raises(AuditDateRangeValidationException) as exc:
            list_audits(
                db,
                date_from=datetime(2026, 11, 22, 0, 0, 0),
                date_to=datetime(2026, 11, 20, 0, 0, 0),
            )

    assert exc.value.status_code == 400
    db.query.assert_not_called()
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_get_audit_returns_record():
    db = MagicMock()
    record = make_audit_record(audit_id=5)
    db.query.return_value.filter.return_value.first.return_value = record

    result = get_audit(db, 5)

    assert result.id == 5


def test_get_audit_raises_404_when_missing(caplog):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with caplog.at_level(logging.WARNING, logger="volumelab.audit"):
        with pytest.raises(AuditNotFoundException) as exc:
            get_audit(db, 999)

    assert exc.value.status_code == 404
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_update_audit_updates_fields_without_user_check_when_unchanged():
    db = MagicMock()
    record = make_audit_record(audit_id=1, user_id=1, action=AuditAction.INSERT)
    db.query.return_value.filter.return_value.first.return_value = record

    result = update_audit(
        db,
        1,
        AuditUpdate(
            action=AuditAction.UPDATE,
            endpoint="/workout-sessions/42/close",
        ),
    )

    assert result.action == AuditAction.UPDATE
    assert result.endpoint == "/workout-sessions/42/close"
    db.execute.assert_not_called()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(record)


def test_update_audit_validates_new_user_exists():
    db = MagicMock()
    record = make_audit_record(audit_id=1, user_id=1)
    db.query.return_value.filter.return_value.first.return_value = record
    db.execute.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        update_audit(db, 1, AuditUpdate(user_id=999))

    assert exc.value.status_code == 404
    db.commit.assert_not_called()


def test_update_audit_allows_clearing_user_id_to_null():
    db = MagicMock()
    record = make_audit_record(audit_id=1, user_id=1)
    db.query.return_value.filter.return_value.first.return_value = record

    result = update_audit(db, 1, AuditUpdate(user_id=None))

    assert result.user_id is None
    db.execute.assert_not_called()
    db.commit.assert_called_once()


def test_update_audit_raises_404_when_record_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(AuditNotFoundException) as exc:
        update_audit(db, 999, AuditUpdate(action=AuditAction.DELETE))

    assert exc.value.status_code == 404


def test_delete_audit_removes_and_commits(caplog):
    db = MagicMock()
    record = make_audit_record(audit_id=1)
    db.query.return_value.filter.return_value.first.return_value = record

    with caplog.at_level(logging.INFO, logger="volumelab.audit"):
        delete_audit(db, 1)

    db.delete.assert_called_once_with(record)
    db.commit.assert_called_once()
    assert any(r.levelno == logging.INFO for r in caplog.records)


def test_delete_audit_raises_404_when_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(AuditNotFoundException) as exc:
        delete_audit(db, 999)

    assert exc.value.status_code == 404
