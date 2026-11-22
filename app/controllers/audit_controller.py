from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit_logger import AuditLogLevel, log_audit_event
from app.core.exceptions import (
    AuditDateRangeValidationException,
    AuditNotFoundException,
)
from app.models.audit_model import AuditAction, AuditModel
from app.schemas.audit_schema import AuditCreate, AuditUpdate


def _ensure_user_exists(db: Session, user_id: int) -> None:
    user_exists = db.execute(
        text("SELECT 1 FROM app_user WHERE id = :user_id"),
        {"user_id": user_id},
    ).first()
    if user_exists is None:
        log_audit_event(
            AuditLogLevel.WARNING,
            event="audit.user_not_found",
            message=f"Intento de asociar auditoría a usuario inexistente ({user_id})",
            user_id=user_id,
            entity="app_user",
            record_id=user_id,
            status_code=status.HTTP_404_NOT_FOUND,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )


def create_audit(db: Session, payload: AuditCreate) -> AuditModel:
    if payload.user_id is not None:
        _ensure_user_exists(db, payload.user_id)

    record = AuditModel(**payload.model_dump())
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        log_audit_event(
            AuditLogLevel.ERROR,
            event="audit.create_failed",
            message="Error al persistir registro de auditoría",
            user_id=payload.user_id,
            entity=payload.entity,
            record_id=payload.record_id,
            action=payload.action,
            endpoint=payload.endpoint,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            exc_info=True,
        )
        raise
    db.refresh(record)

    log_audit_event(
        AuditLogLevel.INFO,
        event="audit.created",
        message="Registro de auditoría creado",
        user_id=record.user_id,
        entity=record.entity,
        record_id=record.record_id,
        action=record.action,
        endpoint=record.endpoint,
        status_code=status.HTTP_201_CREATED,
        details={"audit_id": record.id},
    )
    return record


def record_audit_event(
    db: Session,
    *,
    entity: str,
    record_id: str | int,
    action: AuditAction | str,
    user_id: int | None = None,
    endpoint: str | None = None,
    level: AuditLogLevel | str = AuditLogLevel.INFO,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditModel:
    """Persiste el evento en `audit` (esquema v4) y emite el log estructurado con severidad y datos de valor."""
    payload = AuditCreate(
        user_id=user_id,
        entity=entity,
        record_id=str(record_id),
        action=action,
        endpoint=endpoint,
    )
    record = create_audit(db, payload)
    if level != AuditLogLevel.INFO or message is not None or details is not None:
        log_audit_event(
            level,
            event="audit.domain_event",
            message=message or f"Evento {record.action.value} sobre {record.entity}",
            user_id=record.user_id,
            entity=record.entity,
            record_id=record.record_id,
            action=record.action,
            endpoint=record.endpoint,
            details={"audit_id": record.id, **(details or {})},
        )
    return record


def list_audits(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None,
    entity: str | None = None,
    record_id: str | None = None,
    action: AuditAction | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AuditModel]:
    if date_from is not None and date_to is not None and date_from > date_to:
        log_audit_event(
            AuditLogLevel.WARNING,
            event="audit.invalid_date_range",
            message="Rango de fechas inválido al consultar auditoría",
            entity="audit",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"date_from": date_from, "date_to": date_to},
        )
        raise AuditDateRangeValidationException()

    query = db.query(AuditModel)
    if user_id is not None:
        query = query.filter(AuditModel.user_id == user_id)
    if entity is not None:
        query = query.filter(AuditModel.entity == entity)
    if record_id is not None:
        query = query.filter(AuditModel.record_id == record_id)
    if action is not None:
        query = query.filter(AuditModel.action == action)
    if date_from is not None:
        query = query.filter(AuditModel.created_at >= date_from)
    if date_to is not None:
        query = query.filter(AuditModel.created_at <= date_to)

    return (
        query.order_by(AuditModel.created_at.desc(), AuditModel.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_audit(db: Session, audit_id: int) -> AuditModel:
    record = db.query(AuditModel).filter(AuditModel.id == audit_id).first()
    if record is None:
        log_audit_event(
            AuditLogLevel.WARNING,
            event="audit.not_found",
            message=f"Registro de auditoría con id {audit_id} no encontrado",
            entity="audit",
            record_id=audit_id,
            status_code=status.HTTP_404_NOT_FOUND,
        )
        raise AuditNotFoundException(audit_id)
    return record


def update_audit(db: Session, audit_id: int, payload: AuditUpdate) -> AuditModel:
    record = get_audit(db, audit_id)

    update_data = payload.model_dump(exclude_unset=True)
    if (
        "user_id" in update_data
        and update_data["user_id"] is not None
        and update_data["user_id"] != record.user_id
    ):
        _ensure_user_exists(db, update_data["user_id"])

    for field, value in update_data.items():
        setattr(record, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        log_audit_event(
            AuditLogLevel.ERROR,
            event="audit.update_failed",
            message=f"Error al actualizar registro de auditoría {audit_id}",
            entity="audit",
            record_id=audit_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"updated_fields": sorted(update_data.keys())},
            exc_info=True,
        )
        raise
    db.refresh(record)

    log_audit_event(
        AuditLogLevel.INFO,
        event="audit.updated",
        message=f"Registro de auditoría {audit_id} actualizado",
        user_id=record.user_id,
        entity=record.entity,
        record_id=record.record_id,
        action=record.action,
        endpoint=record.endpoint,
        status_code=status.HTTP_200_OK,
        details={"audit_id": record.id, "updated_fields": sorted(update_data.keys())},
    )
    return record


def delete_audit(db: Session, audit_id: int) -> None:
    record = get_audit(db, audit_id)
    snapshot = {
        "audit_id": record.id,
        "user_id": record.user_id,
        "entity": record.entity,
        "record_id": record.record_id,
        "action": record.action,
        "endpoint": record.endpoint,
    }
    db.delete(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        log_audit_event(
            AuditLogLevel.ERROR,
            event="audit.delete_failed",
            message=f"Error al eliminar registro de auditoría {audit_id}",
            entity="audit",
            record_id=audit_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            exc_info=True,
        )
        raise

    log_audit_event(
        AuditLogLevel.INFO,
        event="audit.deleted",
        message=f"Registro de auditoría {audit_id} eliminado",
        user_id=snapshot["user_id"],
        entity=snapshot["entity"],
        record_id=snapshot["record_id"],
        action=snapshot["action"],
        endpoint=snapshot["endpoint"],
        status_code=status.HTTP_204_NO_CONTENT,
        details={"audit_id": snapshot["audit_id"]},
    )
