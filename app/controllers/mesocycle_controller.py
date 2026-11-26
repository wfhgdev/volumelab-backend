from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.controllers.audit_controller import record_audit_event
from app.models.audit_model import AuditAction
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.app_user_model import AppUserModel
from app.schemas.mesocycle_schema import MesocycleCreate, MesocycleUpdate
from app.core.dependencies import AuditContext
from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.core.exceptions import (
    MesocycleNotFoundException,
    UserNotFoundException,
    MesocycleDateValidationException
)


def get_mesocycles(
    db: Session,
    current_user: AppUserModel | None = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[MesocycleModel]:
    query = select(MesocycleModel)
    if current_user is not None and not is_admin(current_user):
        query = query.filter(MesocycleModel.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(MesocycleModel.user_id == user_id)
    if status is not None:
        query = query.filter(MesocycleModel.status == status)
    query = query.offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_mesocycle_by_id(db: Session, mesocycle_id: int, current_user: AppUserModel | None = None) -> MesocycleModel:
    mesocycle = db.get(MesocycleModel, mesocycle_id)
    if not mesocycle:
        raise MesocycleNotFoundException(mesocycle_id)
    if current_user is not None:
        ensure_owner_or_admin(current_user, mesocycle.user_id, is_private=True)
    return mesocycle


def create_mesocycle(
    db: Session,
    mesocycle: MesocycleCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> MesocycleModel:
    # Validar fechas
    if mesocycle.end_date < mesocycle.start_date:
        raise MesocycleDateValidationException("end_date debe ser mayor o igual a start_date")

    if current_user is not None:
        owner_id = resolve_owner_id(current_user, mesocycle.user_id)
    else:
        owner_id = mesocycle.user_id

    # Validar existencia del usuario
    user = db.get(AppUserModel, owner_id)
    if not user:
        raise UserNotFoundException(owner_id)

    db_mesocycle = MesocycleModel(
        user_id=owner_id,
        name=mesocycle.name,
        start_date=mesocycle.start_date,
        end_date=mesocycle.end_date,
        status=MesocycleStatus(mesocycle.status.value)
    )
    db.add(db_mesocycle)
    db.flush()
    if audit_context is not None:
        record_audit_event(db, "mesocycle", str(db_mesocycle.id), AuditAction.INSERT, audit_context)
    db.commit()
    db.refresh(db_mesocycle)
    return db_mesocycle


def update_mesocycle(
    db: Session,
    mesocycle_id: int,
    mesocycle_update: MesocycleUpdate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> MesocycleModel:
    db_mesocycle = get_mesocycle_by_id(db, mesocycle_id, current_user)

    # Validar coherencia de fechas combinadas
    effective_start = (
        mesocycle_update.start_date
        if mesocycle_update.start_date is not None
        else db_mesocycle.start_date
    )
    effective_end = (
        mesocycle_update.end_date
        if mesocycle_update.end_date is not None
        else db_mesocycle.end_date
    )

    if effective_end < effective_start:
        raise MesocycleDateValidationException("end_date debe ser mayor o igual a start_date")

    update_data = mesocycle_update.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = MesocycleStatus(update_data["status"].value)

    for key, value in update_data.items():
        setattr(db_mesocycle, key, value)

    if audit_context is not None:
        record_audit_event(db, "mesocycle", str(db_mesocycle.id), AuditAction.UPDATE, audit_context)
    db.commit()
    db.refresh(db_mesocycle)
    return db_mesocycle


def delete_mesocycle(
    db: Session,
    mesocycle_id: int,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> None:
    db_mesocycle = get_mesocycle_by_id(db, mesocycle_id, current_user)
    record_id = str(db_mesocycle.id)
    db.delete(db_mesocycle)
    if audit_context is not None:
        record_audit_event(db, "mesocycle", record_id, AuditAction.DELETE, audit_context)
    db.commit()
