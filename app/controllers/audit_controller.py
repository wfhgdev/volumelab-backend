from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import AuditContext
from app.core.exceptions import (
    AuditDateRangeValidationException,
    AuditNotFoundException,
)
from app.models.audit_model import AuditAction, AuditModel
from app.schemas.audit_schema import AuditCreate


def _ensure_user_exists(db: Session, user_id: int) -> None:
    user_exists = db.execute(
        text("SELECT 1 FROM app_user WHERE id = :user_id"),
        {"user_id": user_id},
    ).first()
    if user_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )


def create_audit(db: Session, payload: AuditCreate) -> AuditModel:
    """Inserción interna de un registro de auditoría."""
    if payload.user_id is not None:
        _ensure_user_exists(db, payload.user_id)

    record = AuditModel(**payload.model_dump())
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record


def record_audit_event(
    db: Session,
    entity: str,
    record_id: str | int,
    action: AuditAction | str,
    context: AuditContext | None = None,
) -> AuditModel:
    """Registra un evento en la tabla `audit` dentro de la transacción activa sin hacer commit."""
    resolved_action = (
        action if isinstance(action, AuditAction) else AuditAction(action)
    )
    endpoint = (
        context.endpoint[:255]
        if context is not None and context.endpoint is not None
        else None
    )
    audit_entry = AuditModel(
        user_id=context.user_id if context is not None else None,
        entity=entity,
        record_id=str(record_id),
        action=resolved_action,
        endpoint=endpoint,
    )
    db.add(audit_entry)
    db.flush()
    return audit_entry


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
        raise AuditNotFoundException(audit_id)
    return record
