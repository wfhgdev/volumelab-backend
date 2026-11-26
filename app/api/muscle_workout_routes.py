from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.controllers import muscle_workout_controller
from app.core.database_connection import get_db
from app.core.dependencies import AuditContext, get_audit_context, get_current_user
from app.models.app_user_model import AppUserModel
from app.models.muscle_workout_model import MuscleRole
from app.schemas.muscle_workout_schema import MuscleWorkoutCreate, MuscleWorkoutResponse, MuscleWorkoutUpdate


router = APIRouter(prefix="/muscle-workouts", tags=["Muscle workout associations"])
PositiveId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[AppUserModel, Depends(get_current_user)]
RequestAuditContext = Annotated[AuditContext, Depends(get_audit_context)]


@router.post("/", response_model=MuscleWorkoutResponse, status_code=201)
def create(
    payload: MuscleWorkoutCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    return muscle_workout_controller.create_muscle_workout(
        db, payload, current_user, audit_context=audit_context
    )


@router.get("/", response_model=list[MuscleWorkoutResponse])
def list_all(
    db: DatabaseSession,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    workout_id: int | None = Query(default=None, gt=0),
    muscle_group_id: int | None = Query(default=None, gt=0),
    muscle_role: MuscleRole | None = None,
):
    return muscle_workout_controller.list_muscle_workouts(
        db, current_user, skip, limit, workout_id, muscle_group_id, muscle_role,
    )


@router.get("/{workout_id}/{muscle_group_id}", response_model=MuscleWorkoutResponse)
def get_one(
    workout_id: PositiveId,
    muscle_group_id: PositiveId,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return muscle_workout_controller.get_muscle_workout(db, workout_id, muscle_group_id, current_user)


@router.put("/{workout_id}/{muscle_group_id}", response_model=MuscleWorkoutResponse)
def update(
    workout_id: PositiveId,
    muscle_group_id: PositiveId,
    payload: MuscleWorkoutUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    return muscle_workout_controller.update_muscle_workout(
        db, workout_id, muscle_group_id, payload, current_user, audit_context=audit_context
    )


@router.delete("/{workout_id}/{muscle_group_id}", status_code=204, response_class=Response)
def delete(
    workout_id: PositiveId,
    muscle_group_id: PositiveId,
    db: DatabaseSession,
    current_user: CurrentUser,
    audit_context: RequestAuditContext,
):
    muscle_workout_controller.delete_muscle_workout(
        db, workout_id, muscle_group_id, current_user, audit_context=audit_context
    )
    return Response(status_code=204)
