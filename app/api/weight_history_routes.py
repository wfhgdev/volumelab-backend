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
from app.schemas.weight_history_schema import (
    WeightHistoryCreate,
    WeightHistoryResponse,
    WeightHistoryUpdate,
)


router = APIRouter(prefix="/weight-history", tags=["Weight history"])


@router.post("/", response_model=WeightHistoryResponse, status_code=status.HTTP_201_CREATED)
def create(payload: WeightHistoryCreate, db: Session = Depends(get_db)):
    return create_weight_history(db, payload)


@router.get("/", response_model=list[WeightHistoryResponse])
def list_all(
    user_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_weight_history(db, skip=skip, limit=limit, user_id=user_id)


@router.get("/{weight_history_id}", response_model=WeightHistoryResponse)
def get_one(weight_history_id: int, db: Session = Depends(get_db)):
    return get_weight_history(db, weight_history_id)


@router.put("/{weight_history_id}", response_model=WeightHistoryResponse)
def update(
    weight_history_id: int,
    payload: WeightHistoryUpdate,
    db: Session = Depends(get_db),
):
    return update_weight_history(db, weight_history_id, payload)


@router.delete("/{weight_history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(weight_history_id: int, db: Session = Depends(get_db)):
    delete_weight_history(db, weight_history_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
