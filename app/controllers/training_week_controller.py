from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.controllers.audit_controller import record_audit_event
from app.core.dependencies import AuditContext
from app.core.permissions import ensure_owner_or_admin, is_admin
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction
from app.models.training_week_model import TrainingWeekModel
from app.models.mesocycle_model import MesocycleModel
from app.schemas.training_week_schema import TrainingWeekCreate, TrainingWeekUpdate
from app.core.exceptions import (
    TrainingWeekNotFoundException,
    TrainingWeekOrderConflictException,
    TrainingWeekDateValidationException,
    MesocycleNotFoundException
)


def get_training_weeks(
    db: Session,
    current_user: AppUserModel | None = None,
    mesocycle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[TrainingWeekModel]:
    query = select(TrainingWeekModel)
    if current_user is not None and not is_admin(current_user):
        query = query.join(MesocycleModel, TrainingWeekModel.mesocycle_id == MesocycleModel.id).filter(
            MesocycleModel.user_id == current_user.id
        )
    if mesocycle_id is not None:
        query = query.filter(TrainingWeekModel.mesocycle_id == mesocycle_id)
    query = query.order_by(TrainingWeekModel.week_order.asc()).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_training_week_by_id(
    db: Session, training_week_id: int, current_user: AppUserModel | None = None
) -> TrainingWeekModel:
    week = db.get(TrainingWeekModel, training_week_id)
    if not week:
        raise TrainingWeekNotFoundException(training_week_id)
    if current_user is not None:
        mesocycle = db.get(MesocycleModel, week.mesocycle_id)
        ensure_owner_or_admin(current_user, mesocycle.user_id if mesocycle else None, is_private=True)
    return week


def create_training_week(
    db: Session,
    training_week: TrainingWeekCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> TrainingWeekModel:
    # 1. Validar fechas de inicio y fin
    if training_week.end_date < training_week.start_date:
        raise TrainingWeekDateValidationException("end_date debe ser mayor o igual a start_date")

    # 2. Validar que exista el mesociclo padre y pertenezca al usuario
    mesocycle = db.get(MesocycleModel, training_week.mesocycle_id)
    if not mesocycle:
        raise MesocycleNotFoundException(training_week.mesocycle_id)
    if current_user is not None:
        ensure_owner_or_admin(current_user, mesocycle.user_id, is_private=True)

    # 3. Validar unicidad de week_order en el mesociclo (RN-16: uq_training_week_order)
    existing_order = db.scalar(
        select(TrainingWeekModel).filter(
            and_(
                TrainingWeekModel.mesocycle_id == training_week.mesocycle_id,
                TrainingWeekModel.week_order == training_week.week_order
            )
        )
    )
    if existing_order:
        raise TrainingWeekOrderConflictException(training_week.mesocycle_id, training_week.week_order)

    db_training_week = TrainingWeekModel(
        mesocycle_id=training_week.mesocycle_id,
        week_order=training_week.week_order,
        start_date=training_week.start_date,
        end_date=training_week.end_date
    )
    db.add(db_training_week)
    db.flush()
    if audit_context is not None:
        record_audit_event(
            db, "training_week", str(db_training_week.id), AuditAction.INSERT, audit_context
        )
    db.commit()
    db.refresh(db_training_week)
    return db_training_week


def update_training_week(
    db: Session,
    training_week_id: int,
    training_week_update: TrainingWeekUpdate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> TrainingWeekModel:
    db_training_week = get_training_week_by_id(db, training_week_id, current_user)

    # Validar coherencia de fechas combinadas
    effective_start = (
        training_week_update.start_date
        if training_week_update.start_date is not None
        else db_training_week.start_date
    )
    effective_end = (
        training_week_update.end_date
        if training_week_update.end_date is not None
        else db_training_week.end_date
    )

    if effective_end < effective_start:
        raise TrainingWeekDateValidationException("end_date debe ser mayor o igual a start_date")

    # Validar mesociclo padre si se actualiza
    target_mesocycle_id = (
        training_week_update.mesocycle_id
        if training_week_update.mesocycle_id is not None
        else db_training_week.mesocycle_id
    )
    if training_week_update.mesocycle_id is not None and training_week_update.mesocycle_id != db_training_week.mesocycle_id:
        mesocycle = db.get(MesocycleModel, target_mesocycle_id)
        if not mesocycle:
            raise MesocycleNotFoundException(target_mesocycle_id)
        if current_user is not None:
            ensure_owner_or_admin(current_user, mesocycle.user_id, is_private=True)

    # Validar unicidad de orden si cambia orden o mesociclo
    target_week_order = (
        training_week_update.week_order
        if training_week_update.week_order is not None
        else db_training_week.week_order
    )
    if (
        target_mesocycle_id != db_training_week.mesocycle_id
        or target_week_order != db_training_week.week_order
    ):
        conflict = db.scalar(
            select(TrainingWeekModel).filter(
                and_(
                    TrainingWeekModel.mesocycle_id == target_mesocycle_id,
                    TrainingWeekModel.week_order == target_week_order,
                    TrainingWeekModel.id != training_week_id
                )
            )
        )
        if conflict:
            raise TrainingWeekOrderConflictException(target_mesocycle_id, target_week_order)

    update_data = training_week_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_training_week, key, value)

    if audit_context is not None:
        record_audit_event(
            db, "training_week", str(db_training_week.id), AuditAction.UPDATE, audit_context
        )
    db.commit()
    db.refresh(db_training_week)
    return db_training_week


def delete_training_week(
    db: Session,
    training_week_id: int,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> None:
    db_training_week = get_training_week_by_id(db, training_week_id, current_user)
    record_id = str(db_training_week.id)
    db.delete(db_training_week)
    if audit_context is not None:
        record_audit_event(db, "training_week", record_id, AuditAction.DELETE, audit_context)
    db.commit()
