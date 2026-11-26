from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.controllers.audit_controller import record_audit_event
from app.core.dependencies import AuditContext
from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction
from app.models.weight_history_model import WeightHistoryModel
from app.schemas.weight_history_schema import WeightHistoryCreate, WeightHistoryUpdate


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


def create_weight_history(
    db: Session,
    payload: WeightHistoryCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WeightHistoryModel:
    if current_user is not None:
        user_id = resolve_owner_id(current_user, payload.user_id)
    else:
        user_id = payload.user_id
    _ensure_user_exists(db, user_id)

    record = WeightHistoryModel(user_id=user_id, weight_kg=payload.weight_kg)
    db.add(record)
    db.flush()
    if audit_context is not None:
        record_audit_event(db, "weight_history", str(record.id), AuditAction.INSERT, audit_context)
    db.commit()
    db.refresh(record)
    return record


def list_weight_history(
    db: Session,
    current_user: AppUserModel | None = None,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None,
) -> list[WeightHistoryModel]:
    query = db.query(WeightHistoryModel)
    if current_user is not None and not is_admin(current_user):
        filter_user_id = current_user.id
    else:
        filter_user_id = user_id

    if filter_user_id is not None:
        query = query.filter(WeightHistoryModel.user_id == filter_user_id)

    return (
        query.order_by(
            WeightHistoryModel.created_at.desc(),
            WeightHistoryModel.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_weight_history(
    db: Session, weight_history_id: int, current_user: AppUserModel | None = None
) -> WeightHistoryModel:
    record = (
        db.query(WeightHistoryModel)
        .filter(WeightHistoryModel.id == weight_history_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de peso no encontrado",
        )
    if current_user is not None:
        ensure_owner_or_admin(current_user, record.user_id, is_private=True)
    return record


def update_weight_history(
    db: Session,
    weight_history_id: int,
    payload: WeightHistoryUpdate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WeightHistoryModel:
    record = get_weight_history(db, weight_history_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "user_id" in update_data and update_data["user_id"] is not None:
        if current_user is not None:
            new_user_id = resolve_owner_id(current_user, update_data["user_id"])
        else:
            new_user_id = update_data["user_id"]
        if new_user_id != record.user_id:
            _ensure_user_exists(db, new_user_id)
        record.user_id = new_user_id

    if "weight_kg" in update_data and update_data["weight_kg"] is not None:
        record.weight_kg = update_data["weight_kg"]

    if audit_context is not None:
        record_audit_event(db, "weight_history", str(record.id), AuditAction.UPDATE, audit_context)
    db.commit()
    db.refresh(record)
    return record


def delete_weight_history(
    db: Session,
    weight_history_id: int,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> None:
    record = get_weight_history(db, weight_history_id, current_user)
    record_id = str(record.id)
    db.delete(record)
    if audit_context is not None:
        record_audit_event(db, "weight_history", record_id, AuditAction.DELETE, audit_context)
    db.commit()
