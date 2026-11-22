from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.app_user_model import AppUserModel, RoleUser
from app.models.muscle_group_model import MuscleGroupModel
from app.schemas.muscle_group_schema import MuscleGroupCreate, MuscleGroupUpdate


def _translate_database_error(exc: DBAPIError) -> HTTPException:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    diagnostic = getattr(exc.orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    context = getattr(diagnostic, "context", "") or ""
    if sqlstate == "23505":
        return HTTPException(409, "A muscle group with this name already exists")
    if sqlstate in {"23503", "23001"}:
        return HTTPException(409, "The operation conflicts with related data")
    if sqlstate in {"23502", "23514", "22P02"}:
        return HTTPException(422, "Muscle group data violates a database constraint")
    if sqlstate == "P0001" and (
        constraint == "muscle_group_admin_only"
        or "fn_muscle_group_admin_only" in context
    ):
        return HTTPException(403, "Only an administrator can create a muscle group")
    return HTTPException(500, "An unexpected database error occurred")


@contextmanager
def _database_operation(db: Session):
    try:
        yield
    except DBAPIError as exc:
        db.rollback()
        raise _translate_database_error(exc) from exc
    except HTTPException:
        db.rollback()
        raise


def _find_muscle_group(
    db: Session, muscle_group_id: int, lock: bool = False,
) -> MuscleGroupModel:
    query = db.query(MuscleGroupModel).filter(MuscleGroupModel.id == muscle_group_id)
    if lock:
        query = query.with_for_update()
    record = query.first()
    if record is None:
        raise HTTPException(404, "Muscle group not found")
    return record


def _validate_administrator(db: Session, created_by: int) -> None:
    creator = (
        db.query(AppUserModel)
        .filter(AppUserModel.id == created_by)
        .with_for_update()
        .first()
    )
    if creator is None:
        raise HTTPException(404, "Muscle group creator not found")
    if RoleUser(creator.role) is not RoleUser.ADMIN:
        raise HTTPException(403, "Only an administrator can create a muscle group")


def _validate_unique_name(
    db: Session, name: str, muscle_group_id: int | None = None,
) -> None:
    query = db.query(MuscleGroupModel).filter(MuscleGroupModel.name == name)
    if muscle_group_id is not None:
        query = query.filter(MuscleGroupModel.id != muscle_group_id)
    if query.first() is not None:
        raise HTTPException(409, "A muscle group with this name already exists")


def create_muscle_group(db: Session, payload: MuscleGroupCreate) -> MuscleGroupModel:
    with _database_operation(db):
        _validate_administrator(db, payload.created_by)
        _validate_unique_name(db, payload.name)
        record = MuscleGroupModel(**payload.model_dump())
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


def list_muscle_groups(
    db: Session, skip: int = 0, limit: int = 100, created_by: int | None = None,
) -> list[MuscleGroupModel]:
    with _database_operation(db):
        query = db.query(MuscleGroupModel)
        if created_by is not None:
            query = query.filter(MuscleGroupModel.created_by == created_by)
        return query.order_by(MuscleGroupModel.id.asc()).offset(skip).limit(limit).all()


def get_muscle_group(db: Session, muscle_group_id: int) -> MuscleGroupModel:
    with _database_operation(db):
        return _find_muscle_group(db, muscle_group_id)


def update_muscle_group(
    db: Session, muscle_group_id: int, payload: MuscleGroupUpdate,
) -> MuscleGroupModel:
    with _database_operation(db):
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


def delete_muscle_group(db: Session, muscle_group_id: int) -> None:
    with _database_operation(db):
        record = _find_muscle_group(db, muscle_group_id, lock=True)
        if inspect(db.get_bind()).has_table("muscle_workout"):
            association = db.execute(
                text("SELECT 1 FROM muscle_workout WHERE muscle_group_id = :group_id LIMIT 1"),
                {"group_id": muscle_group_id},
            ).first()
            if association is not None:
                raise HTTPException(409, "A muscle group associated with workouts cannot be deleted")
        db.delete(record)
        db.commit()
