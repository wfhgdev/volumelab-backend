from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.controllers.audit_controller import record_audit_event
from app.core.config import settings
from app.core.dependencies import AuditContext
from app.core.security import create_access_token, hash_password, verify_password
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse


def register_user(
    db: Session,
    payload: RegisterRequest,
    endpoint: str = "POST /auth/register",
) -> AppUserModel:
    existing = db.query(AppUserModel).filter(
        func.lower(AppUserModel.email) == payload.email.lower()
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya existe",
        )

    user = AppUserModel(
        name=payload.name,
        lastname=payload.lastname,
        email=payload.email,
        password_hash=hash_password(payload.password),
        birth_date=payload.birth_date,
        gender=payload.gender,
        height_cm=payload.height_cm,
        role="CLIENTE",
        status="ACTIVO",
    )
    db.add(user)
    db.flush()
    audit_context = AuditContext(user_id=user.id, endpoint=endpoint[:255])
    record_audit_event(db, "app_user", str(user.id), AuditAction.INSERT, audit_context)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    user = db.query(AppUserModel).filter(
        func.lower(AppUserModel.email) == payload.email.strip().lower()
    ).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == "BLOQUEADO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario bloqueado",
        )

    if user.status != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def get_current_user_profile(current_user: AppUserModel) -> AppUserModel:
    return current_user
