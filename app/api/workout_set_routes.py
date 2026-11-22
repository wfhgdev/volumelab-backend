from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.controllers.workout_set_controller import (
    create_workout_set,
    delete_workout_set,
    get_workout_set,
    list_workout_sets,
    update_workout_set,
)
from app.core.database_connection import get_db
from app.schemas.workout_set_schema import (
    WorkoutSetCreate,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)


router = APIRouter(prefix="/workout-sets", tags=["Workout sets"])


@router.post("/", response_model=WorkoutSetResponse, status_code=status.HTTP_201_CREATED)
def create(payload: WorkoutSetCreate, db: Session = Depends(get_db)):
    return create_workout_set(db, payload)


@router.get("/", response_model=list[WorkoutSetResponse])
def list_all(
    session_id: int | None = Query(default=None, gt=0),
    exercise_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_workout_sets(
        db,
        skip=skip,
        limit=limit,
        session_id=session_id,
        exercise_id=exercise_id,
    )


@router.get("/{workout_set_id}", response_model=WorkoutSetResponse)
def get_one(workout_set_id: int, db: Session = Depends(get_db)):
    return get_workout_set(db, workout_set_id)


@router.put("/{workout_set_id}", response_model=WorkoutSetResponse)
def update(
    workout_set_id: int,
    payload: WorkoutSetUpdate,
    db: Session = Depends(get_db),
):
    return update_workout_set(db, workout_set_id, payload)


@router.delete("/{workout_set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(workout_set_id: int, db: Session = Depends(get_db)):
    delete_workout_set(db, workout_set_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
