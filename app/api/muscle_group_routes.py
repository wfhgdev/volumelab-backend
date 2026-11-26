from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.controllers import muscle_group_controller
from app.core.database_connection import get_db
from app.core.dependencies import AuditContext, get_audit_context, get_current_user, require_admin
from app.models.app_user_model import AppUserModel
from app.schemas.muscle_group_schema import (
    MuscleGroupCreate,
    MuscleGroupResponse,
    MuscleGroupUpdate,
)

router = APIRouter(prefix="/muscle-groups", tags=["Muscle groups"])
MuscleGroupId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]
RequestAuditContext = Annotated[AuditContext, Depends(get_audit_context)]


@router.post("/", response_model=MuscleGroupResponse, status_code=201)
def create(
    payload: MuscleGroupCreate,
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    return muscle_group_controller.create_muscle_group(
        db, payload, current_user, audit_context=audit_context
    )


@router.get("/", response_model=list[MuscleGroupResponse])
def list_all(
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    created_by: int | None = Query(default=None, gt=0),
):
    return muscle_group_controller.list_muscle_groups(db, skip, limit, created_by, current_user)


@router.get("/{muscle_group_id}", response_model=MuscleGroupResponse)
def get_one(
    muscle_group_id: MuscleGroupId,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: DatabaseSession,
):
    return muscle_group_controller.get_muscle_group(db, muscle_group_id, current_user)


@router.put("/{muscle_group_id}", response_model=MuscleGroupResponse)
def update(
    muscle_group_id: MuscleGroupId,
    payload: MuscleGroupUpdate,
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    return muscle_group_controller.update_muscle_group(
        db, muscle_group_id, payload, current_user, audit_context=audit_context
    )


@router.delete("/{muscle_group_id}", status_code=204, response_class=Response)
def delete(
    muscle_group_id: MuscleGroupId,
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    db: DatabaseSession,
    audit_context: RequestAuditContext,
):
    muscle_group_controller.delete_muscle_group(
        db, muscle_group_id, current_user, audit_context=audit_context
    )
    return Response(status_code=204)
