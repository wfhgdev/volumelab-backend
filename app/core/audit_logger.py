from datetime import datetime, timezone
import enum
import json
import logging
from typing import Any


class AuditLogLevel(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


_LEVEL_MAP = {
    AuditLogLevel.INFO: logging.INFO,
    AuditLogLevel.WARNING: logging.WARNING,
    AuditLogLevel.ERROR: logging.ERROR,
    AuditLogLevel.CRITICAL: logging.CRITICAL,
}

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "private_key",
    }
)


def sanitize_value_data(data: Any) -> Any:
    """Enmascara recursivamente claves sensibles para evitar filtrar credenciales en logs."""
    if isinstance(data, dict):
        return {
            key: (
                "[REDACTED]"
                if str(key).strip().lower() in _SENSITIVE_KEYS
                else sanitize_value_data(val)
            )
            for key, val in data.items()
        }
    if isinstance(data, list):
        return [sanitize_value_data(item) for item in data]
    if isinstance(data, enum.Enum):
        return data.value
    if isinstance(data, datetime):
        return data.isoformat()
    return data


class JsonAuditFormatter(logging.Formatter):
    """Formateador JSON estructurado para trazabilidad de auditoría y observabilidad."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        audit_data = getattr(record, "audit_data", None)
        if isinstance(audit_data, dict):
            payload.update(sanitize_value_data(audit_data))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_audit_logger(name: str = "volumelab.audit") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonAuditFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


audit_logger = get_audit_logger()


def log_audit_event(
    level: AuditLogLevel | str,
    event: str,
    message: str,
    *,
    user_id: int | None = None,
    entity: str | None = None,
    record_id: str | int | None = None,
    action: str | enum.Enum | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    status_code: int | None = None,
    details: dict[str, Any] | None = None,
    exc_info: bool = False,
) -> dict[str, Any]:
    """Emite un evento estructurado de auditoría en el nivel especificado (INFO, WARNING, ERROR, CRITICAL)."""
    resolved_level = (
        level if isinstance(level, AuditLogLevel) else AuditLogLevel(str(level).upper())
    )
    resolved_action = action.value if isinstance(action, enum.Enum) else action

    audit_data: dict[str, Any] = {
        "event": event,
        "user_id": user_id,
        "entity": entity,
        "record_id": str(record_id) if record_id is not None else None,
        "action": resolved_action,
        "endpoint": endpoint,
        "http_method": http_method,
        "status_code": status_code,
        "details": sanitize_value_data(details) if details is not None else None,
    }
    clean_data = {k: v for k, v in audit_data.items() if v is not None}

    audit_logger.log(
        _LEVEL_MAP[resolved_level],
        message,
        extra={"audit_data": clean_data},
        exc_info=exc_info,
    )
    return clean_data
