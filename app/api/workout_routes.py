from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.controllers import workout_controller
from app.core.database_connection import get_db
from app.core.dependencies import AuditContext, get_audit_context, get_current_user
from app.models.app_user_model import AppUserModel
from app.models.workout_model import ExerciseType
from app.schemas.workout_schema import WorkoutCreate, WorkoutResponse, WorkoutUpdate

router = APIRouter(prefix="/workouts", tags=["Workouts"])
WorkoutId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]
RequestAuditContext = Annotated[AuditContext, Depends(get_audit_context)]


@router.post("/", response_model=WorkoutResponse, status_code=201)
def create(
    payload: WorkoutCreate,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    return workout_controller.create_workout(db, payload, current_user, audit_context=audit_context)


@router.get("/", response_model=list[WorkoutResponse])
def list_all(
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    created_by: int | None = Query(default=None, gt=0),
    exercise_type: ExerciseType | None = Query(default=None, alias="type"),
    public: bool | None = None,
    state: bool | None = None,
):
    return workout_controller.list_workouts(
        db, skip, limit, created_by, exercise_type, public, state, current_user,
    )


@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_one(
    workout_id: WorkoutId,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
):
    return workout_controller.get_workout(db, workout_id, current_user)


@router.put("/{workout_id}", response_model=WorkoutResponse)
def update(
    workout_id: WorkoutId,
    payload: WorkoutUpdate,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    return workout_controller.update_workout(
        db, workout_id, payload, current_user, audit_context=audit_context
    )


@router.delete("/{workout_id}", status_code=204, response_class=Response)
def delete(
    workout_id: WorkoutId,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    workout_controller.delete_workout(db, workout_id, current_user, audit_context=audit_context)
    return Response(status_code=204)
