from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database_connection import get_db
from app.controllers.app_user_controller import (
    create_app_user,
    delete_app_user,
    get_app_user,
    list_app_users,
    update_app_user,
)
from app.schemas.app_user_schema import AppUserCreate, AppUserResponse, AppUserUpdate


router = APIRouter(prefix="/app-users", tags=["App users"])


@router.post("/", response_model=AppUserResponse, status_code=status.HTTP_201_CREATED)
def create(payload: AppUserCreate, db: Session = Depends(get_db)):
    return create_app_user(db, payload)


@router.get("/", response_model=list[AppUserResponse])
def list_all(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_app_users(db, skip, limit)


@router.get("/{app_user_id}", response_model=AppUserResponse)
def get_one(app_user_id: int, db: Session = Depends(get_db)):
    return get_app_user(db, app_user_id)


@router.put("/{app_user_id}", response_model=AppUserResponse)
def update(app_user_id: int, payload: AppUserUpdate, db: Session = Depends(get_db)):
    return update_app_user(db, app_user_id, payload)


@router.delete("/{app_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(app_user_id: int, db: Session = Depends(get_db)):
    delete_app_user(db, app_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
