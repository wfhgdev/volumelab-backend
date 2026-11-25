from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.audit_model import AuditAction
from app.schemas.audit_schema import AuditCreate, AuditResponse


def test_audit_create_minimal_cleans_text_and_allows_nulls():
    payload = AuditCreate(
        entity="  workout_session  ",
        record_id="  42  ",
        action="INSERT",
    )
    assert payload.user_id is None
    assert payload.entity == "workout_session"
    assert payload.record_id == "42"
    assert payload.action == AuditAction.INSERT
    assert payload.endpoint is None


@pytest.mark.parametrize("action", ["INSERT", "UPDATE", "DELETE", "EXPORT"])
def test_audit_create_accepts_all_valid_actions(action):
    payload = AuditCreate(
        user_id=1,
        entity="workout_set",
        record_id="100",
        action=action,
        endpoint="  /workout-sets/100  ",
    )
    assert payload.action.value == action
    assert payload.endpoint == "/workout-sets/100"


@pytest.mark.parametrize("action", ["SELECT", "LOGIN", "PATCH", ""])
def test_audit_create_rejects_invalid_action(action):
    with pytest.raises(ValidationError):
        AuditCreate(entity="audit", record_id="1", action=action)


@pytest.mark.parametrize("user_id", [0, -5, True, False])
def test_audit_create_rejects_invalid_user_id(user_id):
    with pytest.raises(ValidationError):
        AuditCreate(user_id=user_id, entity="app_user", record_id="1", action="INSERT")


@pytest.mark.parametrize("field_name", ["entity", "record_id", "endpoint"])
def test_audit_create_rejects_blank_text_fields(field_name):
    data = {"entity": "app_user", "record_id": "1", "action": "INSERT"}
    data[field_name] = "   "
    with pytest.raises(ValidationError):
        AuditCreate(**data)


def test_audit_create_rejects_oversized_fields():
    with pytest.raises(ValidationError):
        AuditCreate(entity="x" * 61, record_id="1", action="INSERT")
    with pytest.raises(ValidationError):
        AuditCreate(entity="workout", record_id="1" * 61, action="INSERT")
    with pytest.raises(ValidationError):
        AuditCreate(entity="workout", record_id="1", action="INSERT", endpoint="/" + "a" * 255)


def test_audit_response_serializes_exact_v4_fields():
    response = AuditResponse(
        id=10,
        user_id=2,
        entity="workout_session",
        record_id="55",
        action=AuditAction.EXPORT,
        endpoint="/exports/sessions",
        created_at=datetime(2026, 11, 21, 12, 0, 0),
    )
    dumped = response.model_dump()
    assert set(dumped.keys()) == {
        "id",
        "user_id",
        "entity",
        "record_id",
        "action",
        "endpoint",
        "created_at",
    }
    assert dumped["id"] == 10
    assert dumped["action"] == AuditAction.EXPORT
