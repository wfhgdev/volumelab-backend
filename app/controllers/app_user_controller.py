from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.app_user_model import AppUserModel
from app.schemas.app_user_schema import AppUserCreate, AppUserUpdate


def create_app_user(db: Session, payload: AppUserCreate) -> AppUserModel:
    existing = db.query(AppUserModel).filter(
        func.lower(AppUserModel.email) == payload.email.lower()
    ).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya existe")

    app_user = AppUserModel(**payload.model_dump())
    db.add(app_user)
    db.commit()
    db.refresh(app_user)
    return app_user


def list_app_users(db: Session, skip: int = 0, limit: int = 100) -> list[AppUserModel]:
    return db.query(AppUserModel).offset(skip).limit(limit).all()


def get_app_user(db: Session, app_user_id: int) -> AppUserModel:
    app_user = db.query(AppUserModel).filter(AppUserModel.id == app_user_id).first()
    if app_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return app_user


def update_app_user(db: Session, app_user_id: int, payload: AppUserUpdate) -> AppUserModel:
    app_user = get_app_user(db, app_user_id)

    if payload.email is not None:
        existing = db.query(AppUserModel).filter(
            func.lower(AppUserModel.email) == payload.email.lower(),
            AppUserModel.id != app_user_id,
        ).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya existe")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app_user, field, value)

    db.commit()
    db.refresh(app_user)
    return app_user


def delete_app_user(db: Session, app_user_id: int) -> None:
    app_user = get_app_user(db, app_user_id)
    db.delete(app_user)
    db.commit()
