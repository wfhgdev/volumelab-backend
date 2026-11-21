from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

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
    db: Session, payload: WeightHistoryCreate
) -> WeightHistoryModel:
    _ensure_user_exists(db, payload.user_id)

    record = WeightHistoryModel(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_weight_history(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None,
) -> list[WeightHistoryModel]:
    query = db.query(WeightHistoryModel)
    if user_id is not None:
        query = query.filter(WeightHistoryModel.user_id == user_id)
    return (
        query.order_by(
            WeightHistoryModel.created_at.desc(),
            WeightHistoryModel.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_weight_history(db: Session, weight_history_id: int) -> WeightHistoryModel:
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
    return record


def update_weight_history(
    db: Session, weight_history_id: int, payload: WeightHistoryUpdate
) -> WeightHistoryModel:
    record = get_weight_history(db, weight_history_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "user_id" in update_data and update_data["user_id"] != record.user_id:
        _ensure_user_exists(db, update_data["user_id"])

    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


def delete_weight_history(db: Session, weight_history_id: int) -> None:
    record = get_weight_history(db, weight_history_id)
    db.delete(record)
    db.commit()
