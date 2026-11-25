from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.permissions import resolve_owner_id
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.muscle_group_model import MuscleGroupModel
from app.schemas.muscle_group_schema import MuscleGroupCreate, MuscleGroupUpdate


def _find_muscle_group(
    db: Session, muscle_group_id: int, lock: bool = False,
) -> MuscleGroupModel:
    query = db.query(MuscleGroupModel).filter(MuscleGroupModel.id == muscle_group_id)
    if lock:
        query = query.with_for_update()
    record = query.first()
    if record is None:
        raise HTTPException(404, "Grupo muscular no encontrado")
    return record


def _validate_administrator(db: Session, created_by: int) -> None:
    creator = (
        db.query(AppUserModel)
        .filter(AppUserModel.id == created_by)
        .with_for_update()
        .first()
    )
    if creator is None:
        raise HTTPException(404, "Usuario creador no encontrado")
    if RoleUser(creator.role) is not RoleUser.ADMIN:
        raise HTTPException(403, "Solo un administrador puede crear o modificar un grupo muscular")


def _validate_unique_name(
    db: Session, name: str, muscle_group_id: int | None = None,
) -> None:
    query = db.query(MuscleGroupModel).filter(MuscleGroupModel.name == name)
    if muscle_group_id is not None:
        query = query.filter(MuscleGroupModel.id != muscle_group_id)
    if query.first() is not None:
        raise HTTPException(409, "Ya existe un grupo muscular con este nombre")


def create_muscle_group(
    db: Session,
    payload: MuscleGroupCreate,
    current_user: AppUserModel | None = None,
) -> MuscleGroupModel:
    if current_user is not None:
        creator_id = resolve_owner_id(current_user, payload.created_by)
    else:
        creator_id = payload.created_by
    _validate_administrator(db, creator_id)
    _validate_unique_name(db, payload.name)
    data = payload.model_dump()
    data["created_by"] = creator_id
    record = MuscleGroupModel(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_muscle_groups(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    created_by: int | None = None,
    current_user: AppUserModel | None = None,
) -> list[MuscleGroupModel]:
    query = db.query(MuscleGroupModel)
    if created_by is not None:
        query = query.filter(MuscleGroupModel.created_by == created_by)
    return query.order_by(MuscleGroupModel.id.asc()).offset(skip).limit(limit).all()


def get_muscle_group(
    db: Session,
    muscle_group_id: int,
    current_user: AppUserModel | None = None,
) -> MuscleGroupModel:
    return _find_muscle_group(db, muscle_group_id)


def update_muscle_group(
    db: Session,
    muscle_group_id: int,
    payload: MuscleGroupUpdate,
    current_user: AppUserModel | None = None,
) -> MuscleGroupModel:
    record = _find_muscle_group(db, muscle_group_id, lock=True)
    changes = payload.model_dump(exclude_unset=True)
    if "created_by" in changes:
        _validate_administrator(db, changes["created_by"])
    if "name" in changes and changes["name"] != record.name:
        _validate_unique_name(db, changes["name"], muscle_group_id)
    for field_name, value in changes.items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return record


def delete_muscle_group(
    db: Session,
    muscle_group_id: int,
    current_user: AppUserModel | None = None,
) -> None:
    record = _find_muscle_group(db, muscle_group_id, lock=True)
    if inspect(db.get_bind()).has_table("muscle_workout"):
        association = db.execute(
            text("SELECT 1 FROM muscle_workout WHERE muscle_group_id = :group_id LIMIT 1"),
            {"group_id": muscle_group_id},
        ).first()
        if association is not None:
            raise HTTPException(409, "No se puede eliminar un grupo muscular asociado a ejercicios")
    db.delete(record)
    db.commit()
