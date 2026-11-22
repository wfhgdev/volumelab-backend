from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.controllers import muscle_group_controller
from app.core.database_connection import get_db
from app.schemas.muscle_group_schema import (
    MuscleGroupCreate, MuscleGroupResponse, MuscleGroupUpdate,
)


router = APIRouter(prefix="/muscle-groups", tags=["Muscle groups"])
MuscleGroupId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=MuscleGroupResponse, status_code=201)
def create(payload: MuscleGroupCreate, db: DatabaseSession):
    return muscle_group_controller.create_muscle_group(db, payload)


@router.get("/", response_model=list[MuscleGroupResponse])
def list_all(
    db: DatabaseSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    created_by: int | None = Query(default=None, gt=0),
):
    return muscle_group_controller.list_muscle_groups(db, skip, limit, created_by)


@router.get("/{muscle_group_id}", response_model=MuscleGroupResponse)
def get_one(muscle_group_id: MuscleGroupId, db: DatabaseSession):
    return muscle_group_controller.get_muscle_group(db, muscle_group_id)


@router.put("/{muscle_group_id}", response_model=MuscleGroupResponse)
def update(
    muscle_group_id: MuscleGroupId, payload: MuscleGroupUpdate, db: DatabaseSession,
):
    return muscle_group_controller.update_muscle_group(db, muscle_group_id, payload)


@router.delete("/{muscle_group_id}", status_code=204, response_class=Response)
def delete(muscle_group_id: MuscleGroupId, db: DatabaseSession):
    muscle_group_controller.delete_muscle_group(db, muscle_group_id)
    return Response(status_code=204)
