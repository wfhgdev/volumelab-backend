from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import ensure_owner_or_admin, is_admin
from app.models.app_user_model import AppUserModel
from app.models.workout_session_model import WorkoutSessionModel
from app.models.workout_set_model import (
    WorkoutSetExerciseType,
    WorkoutSetModel,
    WorkoutSetSessionStatus,
)
from app.schemas.workout_set_schema import WorkoutSetCreate, WorkoutSetUpdate


def _quantize(value: Decimal, quantum: str) -> Decimal:
    return value.quantize(Decimal(quantum))


def _get_session_bodyweight(db: Session, session_id: int) -> Decimal | None:
    row = db.execute(
        text(
            "SELECT current_bodyweight_kg, status "
            "FROM workout_session WHERE id = :session_id"
        ),
        {"session_id": session_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesión con id {session_id} no encontrada",
        )
    session_status = row["status"]
    if isinstance(session_status, WorkoutSetSessionStatus):
        session_status = session_status.value
    if str(session_status) == WorkoutSetSessionStatus.CERRADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La sesión {session_id} está cerrada; sus series no se pueden modificar",
        )
    bodyweight = row["current_bodyweight_kg"]
    return Decimal(str(bodyweight)) if bodyweight is not None else None


def _get_exercise_info(db: Session, exercise_id: int) -> tuple[bool, str, bool, bool, bool]:
    row = db.execute(
        text(
            "SELECT is_bodyweight, type, allow_positive_ballast, "
            "allow_negative_ballast, state FROM workout WHERE id = :exercise_id"
        ),
        {"exercise_id": exercise_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejercicio con id {exercise_id} no encontrado",
        )
    if not bool(row["state"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El ejercicio {exercise_id} está desactivado",
        )
    exercise_type = row["type"]
    if isinstance(exercise_type, WorkoutSetExerciseType):
        exercise_type = exercise_type.value
    return (
        bool(row["is_bodyweight"]),
        str(exercise_type),
        bool(row["allow_positive_ballast"]),
        bool(row["allow_negative_ballast"]),
        bool(row["state"]),
    )


def _validate_reps_duration(reps: int | None, duration_second: int | None) -> None:
    if (reps is None) == (duration_second is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe indicar exactamente uno de reps o duration_second",
        )


def _validate_ballast(
    added_weight_kg: Decimal | None,
    allow_positive: bool,
    allow_negative: bool,
) -> None:
    if added_weight_kg is None:
        return
    value = Decimal(added_weight_kg)
    if value > 0 and not allow_positive:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El ejercicio no permite lastre positivo",
        )
    if value < 0 and not allow_negative:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El ejercicio no permite asistencia o lastre negativo",
        )


def _effective_weight(
    bodyweight: Decimal | None,
    is_bodyweight: bool,
    added_weight_kg: Decimal | None,
) -> Decimal:
    if not is_bodyweight:
        if added_weight_kg is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="added_weight_kg es obligatorio en ejercicios con peso externo",
            )
        value = Decimal(added_weight_kg)
        if value <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="added_weight_kg debe ser mayor que 0 en ejercicios con peso externo",
            )
        return value
    if bodyweight is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_bodyweight_kg de la sesión es obligatorio en ejercicios corporales",
        )
    added = Decimal(added_weight_kg) if added_weight_kg is not None else Decimal("0")
    value = bodyweight + added if added >= 0 else bodyweight - abs(added)
    if value <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_weight_kg resultante debe ser mayor que 0",
        )
    return value


def _calculate_values(
    db: Session,
    session_id: int,
    exercise_id: int,
    added_weight_kg: Decimal | None,
    reps: int | None,
    duration_second: int | None,
    rir: int | None,
) -> tuple[Decimal, Decimal | None, Decimal | None, Decimal | None]:
    bodyweight = _get_session_bodyweight(db, session_id)
    is_bodyweight, exercise_type, allow_positive, allow_negative, _ = _get_exercise_info(
        db, exercise_id
    )
    _validate_ballast(added_weight_kg, allow_positive, allow_negative)
    _validate_reps_duration(reps, duration_second)

    dynamic = WorkoutSetExerciseType.DINAMICO.value
    isometric = WorkoutSetExerciseType.ISOMETRICO.value
    if exercise_type == dynamic and reps is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un ejercicio dinámico exige reps",
        )
    if exercise_type == isometric and duration_second is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un ejercicio isométrico exige duration_second",
        )

    effective = _effective_weight(bodyweight, is_bodyweight, added_weight_kg)
    if exercise_type == isometric:
        volume_load = _quantize(effective * Decimal(duration_second), "0.001")
        return effective, volume_load, None, None

    if rir is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="rir es obligatorio en series dinámicas para calcular el 1RM",
        )
    raw_one_rm = effective * (Decimal("1") + (Decimal(reps + rir) / Decimal("30")))
    volume_load = _quantize(effective * Decimal(reps), "0.001")
    one_rm_kg = _quantize(raw_one_rm, "0.01")
    one_rm_percentage = _quantize((effective / raw_one_rm) * Decimal("100"), "0.01")
    return effective, volume_load, one_rm_kg, one_rm_percentage


def _raise_integrity_error(exc: IntegrityError) -> None:
    original = getattr(exc, "orig", None)
    message = str(original) if original is not None else str(exc)
    lowered = message.lower()
    if "uq_workout_set_position" in lowered or "unique" in lowered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una serie con esa posición en la sesión",
        )
    if "fk_workout_set_session" in lowered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    if "fk_workout_set_exercise" in lowered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ejercicio no encontrado",
        )
    if "chk_set" in lowered or "check" in lowered:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La serie no cumple las restricciones de la base de datos",
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Error de integridad al guardar la serie",
    )


def _raise_dbapi_error(exc: DBAPIError) -> None:
    original = getattr(exc, "orig", None)
    message = str(original) if original is not None else str(exc)
    lowered = message.lower()
    if "ya tiene otro ejercicio" in lowered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe otro ejercicio en esa posición de la sesión",
        )
    if "rn-07" in lowered or "cerrada" in lowered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )
    if "rn-04" in lowered or "rn-10" in lowered or "rn-12" in lowered:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Error en base de datos: {message}",
    )


def create_workout_set(
    db: Session, payload: WorkoutSetCreate, current_user: AppUserModel | None = None
) -> WorkoutSetModel:
    session = db.get(WorkoutSessionModel, payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesión con id {payload.session_id} no encontrada",
        )
    if current_user is not None:
        ensure_owner_or_admin(current_user, session.user_id, is_private=not session.public)

    effective, volume_load, one_rm_kg, one_rm_percentage = _calculate_values(
        db,
        payload.session_id,
        payload.exercise_id,
        payload.added_weight_kg,
        payload.reps,
        payload.duration_second,
        payload.rir,
    )
    record = WorkoutSetModel(
        session_id=payload.session_id,
        exercise_id=payload.exercise_id,
        exercise_order=payload.exercise_order,
        set_number=payload.set_number,
        added_weight_kg=payload.added_weight_kg,
        reps=payload.reps,
        duration_second=payload.duration_second,
        rir=payload.rir,
        note=payload.note,
        completed=payload.completed,
        effective_weight_kg=effective,
        volume_load=volume_load,
        one_rm_kg=one_rm_kg,
        one_rm_percentage=one_rm_percentage,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except IntegrityError as exc:
        db.rollback()
        _raise_integrity_error(exc)
    except DBAPIError as exc:
        db.rollback()
        _raise_dbapi_error(exc)


def list_workout_sets(
    db: Session,
    current_user: AppUserModel | None = None,
    skip: int = 0,
    limit: int = 100,
    session_id: int | None = None,
    exercise_id: int | None = None,
) -> list[WorkoutSetModel]:
    query = db.query(WorkoutSetModel)
    if current_user is not None and not is_admin(current_user):
        query = query.join(WorkoutSessionModel, WorkoutSetModel.session_id == WorkoutSessionModel.id).filter(
            or_(
                WorkoutSessionModel.user_id == current_user.id,
                WorkoutSessionModel.public.is_(True),
            )
        )
    if session_id is not None:
        query = query.filter(WorkoutSetModel.session_id == session_id)
    if exercise_id is not None:
        query = query.filter(WorkoutSetModel.exercise_id == exercise_id)
    return (
        query.order_by(
            WorkoutSetModel.session_id,
            WorkoutSetModel.exercise_order,
            WorkoutSetModel.set_number,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_workout_set(
    db: Session, workout_set_id: int, current_user: AppUserModel | None = None
) -> WorkoutSetModel:
    record = (
        db.query(WorkoutSetModel)
        .filter(WorkoutSetModel.id == workout_set_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Serie con id {workout_set_id} no encontrada",
        )
    if current_user is not None and not is_admin(current_user):
        session = db.get(WorkoutSessionModel, record.session_id)
        if session and session.user_id != current_user.id and not session.public:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Serie con id {workout_set_id} no encontrada",
            )
    return record


def update_workout_set(
    db: Session,
    workout_set_id: int,
    payload: WorkoutSetUpdate,
    current_user: AppUserModel | None = None,
) -> WorkoutSetModel:
    record = get_workout_set(db, workout_set_id, current_user)
    if current_user is not None:
        session = db.get(WorkoutSessionModel, record.session_id)
        ensure_owner_or_admin(
            current_user,
            session.user_id if session else None,
            is_private=not (session.public if session else False),
        )

        if payload.session_id is not None and payload.session_id != record.session_id:
            target_session = db.get(WorkoutSessionModel, payload.session_id)
            if not target_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sesión con id {payload.session_id} no encontrada",
                )
            ensure_owner_or_admin(
                current_user,
                target_session.user_id,
                is_private=not target_session.public,
            )

    _get_session_bodyweight(db, record.session_id)
    calculated_fields = {
        "effective_weight_kg",
        "volume_load",
        "one_rm_kg",
        "one_rm_percentage",
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field not in calculated_fields:
            setattr(record, field, value)

    effective, volume_load, one_rm_kg, one_rm_percentage = _calculate_values(
        db,
        record.session_id,
        record.exercise_id,
        record.added_weight_kg,
        record.reps,
        record.duration_second,
        record.rir,
    )
    record.effective_weight_kg = effective
    record.volume_load = volume_load
    record.one_rm_kg = one_rm_kg
    record.one_rm_percentage = one_rm_percentage

    try:
        db.commit()
        db.refresh(record)
        return record
    except IntegrityError as exc:
        db.rollback()
        _raise_integrity_error(exc)
    except DBAPIError as exc:
        db.rollback()
        _raise_dbapi_error(exc)


def delete_workout_set(
    db: Session, workout_set_id: int, current_user: AppUserModel | None = None
) -> None:
    record = get_workout_set(db, workout_set_id, current_user)
    if current_user is not None:
        session = db.get(WorkoutSessionModel, record.session_id)
        ensure_owner_or_admin(
            current_user,
            session.user_id if session else None,
            is_private=not (session.public if session else False),
        )
    _get_session_bodyweight(db, record.session_id)
    try:
        db.delete(record)
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        _raise_dbapi_error(exc)
