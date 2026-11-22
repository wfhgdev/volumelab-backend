import json
import logging

import pytest

from app.core.audit_logger import (
    AuditLogLevel,
    JsonAuditFormatter,
    log_audit_event,
    sanitize_value_data,
)


@pytest.mark.parametrize(
    ("level", "expected_logging_level"),
    [
        (AuditLogLevel.INFO, logging.INFO),
        (AuditLogLevel.WARNING, logging.WARNING),
        (AuditLogLevel.ERROR, logging.ERROR),
        (AuditLogLevel.CRITICAL, logging.CRITICAL),
    ],
)
def test_log_audit_event_emits_all_supported_levels(caplog, level, expected_logging_level):
    with caplog.at_level(logging.INFO, logger="volumelab.audit"):
        data = log_audit_event(
            level,
            event="audit.test",
            message=f"Mensaje de nivel {level.value}",
            user_id=1,
            entity="workout_session",
            record_id=42,
            action="INSERT",
            endpoint="/workout-sessions/42",
            http_method="POST",
            status_code=201,
            details={"title": "Torso A"},
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == expected_logging_level
    assert data["entity"] == "workout_session"
    assert data["record_id"] == "42"
    assert data["details"] == {"title": "Torso A"}


def test_log_audit_event_rejects_unsupported_level():
    with pytest.raises(ValueError):
        log_audit_event("DEBUG", event="audit.test", message="no permitido")


def test_sanitize_value_data_redacts_sensitive_fields_recursively():
    sanitized = sanitize_value_data(
        {
            "email": "user@volumelab.com",
            "password": "plain",
            "nested": {
                "password_hash": "hash123",
                "access_token": "jwt",
                "safe_metric": 100,
            },
            "items": [{"Authorization": "Bearer secret"}, {"reps": 10}],
        }
    )

    assert sanitized["email"] == "user@volumelab.com"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["password_hash"] == "[REDACTED]"
    assert sanitized["nested"]["access_token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_metric"] == 100
    assert sanitized["items"][0]["Authorization"] == "[REDACTED]"
    assert sanitized["items"][1]["reps"] == 10


def test_json_audit_formatter_outputs_valid_json_with_sanitized_data():
    formatter = JsonAuditFormatter()
    record = logging.LogRecord(
        name="volumelab.audit",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="Intento bloqueado por RN-07",
        args=(),
        exc_info=None,
    )
    record.audit_data = {
        "event": "workout_set.blocked",
        "entity": "workout_set",
        "record_id": "10",
        "details": {"token": "abc", "rule": "RN-07"},
    }

    parsed = json.loads(formatter.format(record))
    assert parsed["level"] == "WARNING"
    assert parsed["event"] == "workout_set.blocked"
    assert parsed["message"] == "Intento bloqueado por RN-07"
    assert parsed["details"]["token"] == "[REDACTED]"
    assert parsed["details"]["rule"] == "RN-07"
    assert "timestamp" in parsed
