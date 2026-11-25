from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.controllers.weight_history_controller import (
    create_weight_history,
    delete_weight_history,
    get_weight_history,
    list_weight_history,
    update_weight_history,
)
from app.core.database_connection import get_db
from app.core.dependencies import get_current_user
from app.models.app_user_model import AppUserModel
from app.schemas.weight_history_schema import (
    WeightHistoryCreate,
    WeightHistoryResponse,
    WeightHistoryUpdate,
)


router = APIRouter(prefix="/weight-history", tags=["Weight history"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[AppUserModel, Depends(get_current_user)]


@router.post("/", response_model=WeightHistoryResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: WeightHistoryCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return create_weight_history(db, payload, current_user)


@router.get("/", response_model=list[WeightHistoryResponse])
def list_all(
    db: DatabaseSession,
    current_user: CurrentUser,
    user_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return list_weight_history(db, current_user, skip=skip, limit=limit, user_id=user_id)


@router.get("/{weight_history_id}", response_model=WeightHistoryResponse)
def get_one(
    weight_history_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return get_weight_history(db, weight_history_id, current_user)


@router.put("/{weight_history_id}", response_model=WeightHistoryResponse)
def update(
    weight_history_id: int,
    payload: WeightHistoryUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return update_weight_history(db, weight_history_id, payload, current_user)


@router.delete("/{weight_history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    weight_history_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    delete_weight_history(db, weight_history_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
