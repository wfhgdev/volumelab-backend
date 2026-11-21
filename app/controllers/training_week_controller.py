from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
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
    mesocycle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[TrainingWeekModel]:
    query = select(TrainingWeekModel)
    if mesocycle_id is not None:
        query = query.filter(TrainingWeekModel.mesocycle_id == mesocycle_id)
    query = query.order_by(TrainingWeekModel.week_order.asc()).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_training_week_by_id(db: Session, training_week_id: int) -> TrainingWeekModel:
    week = db.get(TrainingWeekModel, training_week_id)
    if not week:
        raise TrainingWeekNotFoundException(training_week_id)
    return week


def create_training_week(db: Session, training_week: TrainingWeekCreate) -> TrainingWeekModel:
    # 1. Validar fechas de inicio y fin
    if training_week.end_date < training_week.start_date:
        raise TrainingWeekDateValidationException("end_date debe ser mayor o igual a start_date")

    # 2. Validar que exista el mesociclo padre
    mesocycle = db.get(MesocycleModel, training_week.mesocycle_id)
    if not mesocycle:
        raise MesocycleNotFoundException(training_week.mesocycle_id)

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
    db.commit()
    db.refresh(db_training_week)
    return db_training_week


def update_training_week(
    db: Session,
    training_week_id: int,
    training_week_update: TrainingWeekUpdate
) -> TrainingWeekModel:
    db_training_week = db.get(TrainingWeekModel, training_week_id)
    if not db_training_week:
        raise TrainingWeekNotFoundException(training_week_id)

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

    db.commit()
    db.refresh(db_training_week)
    return db_training_week


def delete_training_week(db: Session, training_week_id: int) -> None:
    db_training_week = db.get(TrainingWeekModel, training_week_id)
    if not db_training_week:
        raise TrainingWeekNotFoundException(training_week_id)

    db.delete(db_training_week)
    db.commit()
