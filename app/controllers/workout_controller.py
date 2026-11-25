from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.permissions import is_admin, resolve_owner_id
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.workout_schema import WorkoutBase, WorkoutCreate, WorkoutUpdate


def _find_workout(db: Session, workout_id: int, lock: bool = False) -> WorkoutModel:
    query = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id)
    if lock:
        query = query.with_for_update()
    workout = query.first()
    if workout is None:
        raise HTTPException(404, "Ejercicio no encontrado")
    return workout


def _validate_creator_and_limit(
    db: Session, created_by: int, public: bool, workout_id: int | None = None,
) -> None:
    creator = (
        db.query(AppUserModel)
        .filter(AppUserModel.id == created_by)
        .with_for_update()
        .first()
    )
    if creator is None:
        raise HTTPException(404, "Usuario creador no encontrado")
    if not public or RoleUser(creator.role) is not RoleUser.CLIENTE:
        return
    query = db.query(WorkoutModel).filter(
        WorkoutModel.created_by == created_by, WorkoutModel.public.is_(True),
    )
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.count() >= 20:
        raise HTTPException(409, "Un cliente puede tener como máximo 20 ejercicios públicos")


def _validate_unique_name(db: Session, name: str, workout_id: int | None = None) -> None:
    query = db.query(WorkoutModel).filter(WorkoutModel.name == name)
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.first() is not None:
        raise HTTPException(409, "Ya existe un ejercicio con este nombre")


def create_workout(
    db: Session,
    payload: WorkoutCreate,
    current_user: AppUserModel | None = None,
) -> WorkoutModel:
    if current_user is not None:
        creator_id = resolve_owner_id(current_user, payload.created_by)
    else:
        creator_id = payload.created_by
    _validate_creator_and_limit(db, creator_id, payload.public)
    _validate_unique_name(db, payload.name)
    data = payload.model_dump()
    data["created_by"] = creator_id
    workout = WorkoutModel(**data)
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


def list_workouts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    created_by: int | None = None,
    exercise_type: ExerciseType | None = None,
    public: bool | None = None,
    state: bool | None = None,
    current_user: AppUserModel | None = None,
) -> list[WorkoutModel]:
    query = db.query(WorkoutModel)

    if current_user is not None and not is_admin(current_user):
        query = query.filter(
            or_(
                WorkoutModel.created_by == current_user.id,
                WorkoutModel.public.is_(True),
            )
        )

    filters = {
        "created_by": created_by,
        "type": exercise_type,
        "public": public,
        "state": state,
    }
    for field_name, value in filters.items():
        if value is not None:
            query = query.filter(getattr(WorkoutModel, field_name) == value)

    return query.order_by(WorkoutModel.id.asc()).offset(skip).limit(limit).all()


def get_workout(
    db: Session,
    workout_id: int,
    current_user: AppUserModel | None = None,
) -> WorkoutModel:
    workout = _find_workout(db, workout_id)
    if current_user is not None and not is_admin(current_user):
        if workout.created_by != current_user.id and not workout.public:
            raise HTTPException(404, "Ejercicio no encontrado")
    return workout


def update_workout(
    db: Session,
    workout_id: int,
    payload: WorkoutUpdate,
    current_user: AppUserModel | None = None,
) -> WorkoutModel:
    workout = _find_workout(db, workout_id, lock=True)

    if current_user is not None and not is_admin(current_user):
        if workout.created_by != current_user.id:
            if workout.public:
                raise HTTPException(403, "No tienes permiso para modificar este ejercicio")
            raise HTTPException(404, "Ejercicio no encontrado")
        if "created_by" in payload.model_fields_set and payload.created_by != current_user.id:
            raise HTTPException(403, "No tienes permiso para modificar este ejercicio")

    changes = payload.model_dump(exclude_unset=True)
    current = {field: getattr(workout, field) for field in WorkoutBase.model_fields}
    try:
        WorkoutBase.model_validate(current | {key: value for key, value in changes.items() if key != "created_by"})
    except ValidationError as exc:
        raise HTTPException(422, "Un lastre negativo requiere un ejercicio con peso corporal") from exc

    if "type" in changes and changes["type"] != workout.type:
        has_sets = db.execute(
            text("SELECT 1 FROM workout_set WHERE exercise_id = :workout_id LIMIT 1"),
            {"workout_id": workout_id},
        ).first()
        if has_sets is not None:
            raise HTTPException(409, "No se puede cambiar el tipo de un ejercicio que ya tiene series registradas")

    if "name" in changes and changes["name"] != workout.name:
        _validate_unique_name(db, changes["name"], workout_id)

    if {"created_by", "public"} & changes.keys():
        target_creator = changes.get("created_by", workout.created_by)
        if target_creator is not None:
            _validate_creator_and_limit(db, target_creator, changes.get("public", workout.public), workout_id)

    for field_name, value in changes.items():
        setattr(workout, field_name, value)

    db.commit()
    db.refresh(workout)
    return workout


def delete_workout(
    db: Session,
    workout_id: int,
    current_user: AppUserModel | None = None,
) -> None:
    workout = _find_workout(db, workout_id, lock=True)

    if current_user is not None and not is_admin(current_user):
        if workout.created_by != current_user.id:
            if workout.public:
                raise HTTPException(403, "No tienes permiso para modificar este ejercicio")
            raise HTTPException(404, "Ejercicio no encontrado")

    workout.state = False
    db.commit()
