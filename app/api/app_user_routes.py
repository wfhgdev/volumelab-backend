from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.controllers.app_user_controller import (
    create_app_user,
    delete_app_user,
    get_app_user,
    list_app_users,
    update_app_user,
)
from app.core.database_connection import get_db
from app.core.dependencies import AuditContext, get_audit_context, get_current_user, require_admin
from app.models.app_user_model import AppUserModel
from app.schemas.app_user_schema import AppUserCreate, AppUserResponse, AppUserUpdate

router = APIRouter(prefix="/app-users", tags=["App users"])


@router.post("/", response_model=AppUserResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: AppUserCreate,
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
    db: Session = Depends(get_db),
):
    return create_app_user(db, payload, audit_context=audit_context)


@router.get("/", response_model=list[AppUserResponse])
def list_all(
    current_user: Annotated[AppUserModel, Depends(require_admin)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_app_users(db, skip, limit, current_user)


@router.get("/{app_user_id}", response_model=AppUserResponse)
def get_one(
    app_user_id: int,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return get_app_user(db, app_user_id, current_user)


@router.put("/{app_user_id}", response_model=AppUserResponse)
def update(
    app_user_id: int,
    payload: AppUserUpdate,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
    db: Session = Depends(get_db),
):
    return update_app_user(db, app_user_id, payload, current_user, audit_context=audit_context)


@router.delete("/{app_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    app_user_id: int,
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
    audit_context: Annotated[AuditContext, Depends(get_audit_context)],
    db: Session = Depends(get_db),
):
    delete_app_user(db, app_user_id, current_user, audit_context=audit_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
