from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.permissions import is_admin
from app.core.security import hash_password
from app.models.app_user_model import AppUserModel
from app.schemas.app_user_schema import AppUserCreate, AppUserUpdate


def create_app_user(db: Session, payload: AppUserCreate) -> AppUserModel:
    existing = db.query(AppUserModel).filter(
        func.lower(AppUserModel.email) == payload.email.lower()
    ).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya existe")

    data = payload.model_dump()
    password = data.pop("password")
    data["password_hash"] = hash_password(password)

    app_user = AppUserModel(**data)
    db.add(app_user)
    db.commit()
    db.refresh(app_user)
    return app_user


def list_app_users(db: Session, skip: int = 0, limit: int = 100, current_user: AppUserModel | None = None) -> list[AppUserModel]:
    if current_user is not None and not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido a administradores")
    return db.query(AppUserModel).offset(skip).limit(limit).all()


def get_app_user(db: Session, app_user_id: int, current_user: AppUserModel | None = None) -> AppUserModel:
    if current_user is not None and not is_admin(current_user) and current_user.id != app_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    app_user = db.query(AppUserModel).filter(AppUserModel.id == app_user_id).first()
    if app_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return app_user


def update_app_user(
    db: Session,
    app_user_id: int,
    payload: AppUserUpdate,
    current_user: AppUserModel | None = None,
) -> AppUserModel:
    if current_user is not None and not is_admin(current_user):
        if current_user.id != app_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        if "role" in payload.model_fields_set or "status" in payload.model_fields_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un administrador puede modificar el rol o estado",
            )

    app_user = get_app_user(db, app_user_id, current_user)

    if payload.email is not None:
        existing = db.query(AppUserModel).filter(
            func.lower(AppUserModel.email) == payload.email.lower(),
            AppUserModel.id != app_user_id,
        ).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya existe")

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        password = update_data.pop("password")
        if password is not None:
            app_user.password_hash = hash_password(password)

    for field, value in update_data.items():
        setattr(app_user, field, value)

    db.commit()
    db.refresh(app_user)
    return app_user


def delete_app_user(
    db: Session,
    app_user_id: int,
    current_user: AppUserModel | None = None,
) -> None:
    if current_user is not None and not is_admin(current_user):
        if current_user.id != app_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    app_user = get_app_user(db, app_user_id, current_user)
    db.delete(app_user)
    db.commit()
