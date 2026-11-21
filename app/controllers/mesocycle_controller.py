from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.mesocycle_model import MesocycleModel, MesocycleStatus
from app.models.user_model import UserModel
from app.schemas.mesocycle_schema import MesocycleCreate, MesocycleUpdate
from app.core.exceptions import (
    MesocycleNotFoundException,
    UserNotFoundException,
    MesocycleDateValidationException
)


def get_mesocycles(
    db: Session,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[MesocycleModel]:
    query = select(MesocycleModel)
    if user_id is not None:
        query = query.filter(MesocycleModel.user_id == user_id)
    if status is not None:
        query = query.filter(MesocycleModel.status == status)
    query = query.offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_mesocycle_by_id(db: Session, mesocycle_id: int) -> MesocycleModel:
    mesocycle = db.get(MesocycleModel, mesocycle_id)
    if not mesocycle:
        raise MesocycleNotFoundException(mesocycle_id)
    return mesocycle


def create_mesocycle(db: Session, mesocycle: MesocycleCreate) -> MesocycleModel:
    # Validar fechas
    if mesocycle.end_date < mesocycle.start_date:
        raise MesocycleDateValidationException("end_date debe ser mayor o igual a start_date")

    # Validar existencia del usuario
    user = db.get(UserModel, mesocycle.user_id)
    if not user:
        raise UserNotFoundException(mesocycle.user_id)

    db_mesocycle = MesocycleModel(
        user_id=mesocycle.user_id,
        name=mesocycle.name,
        start_date=mesocycle.start_date,
        end_date=mesocycle.end_date,
        status=MesocycleStatus(mesocycle.status.value)
    )
    db.add(db_mesocycle)
    db.commit()
    db.refresh(db_mesocycle)
    return db_mesocycle


def update_mesocycle(
    db: Session,
    mesocycle_id: int,
    mesocycle_update: MesocycleUpdate
) -> MesocycleModel:
    db_mesocycle = db.get(MesocycleModel, mesocycle_id)
    if not db_mesocycle:
        raise MesocycleNotFoundException(mesocycle_id)

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

    db.commit()
    db.refresh(db_mesocycle)
    return db_mesocycle


def delete_mesocycle(db: Session, mesocycle_id: int) -> None:
    db_mesocycle = db.get(MesocycleModel, mesocycle_id)
    if not db_mesocycle:
        raise MesocycleNotFoundException(mesocycle_id)

    db.delete(db_mesocycle)
    db.commit()
