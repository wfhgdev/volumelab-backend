from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.controllers import auth_controller
from app.core.database_connection import get_db
from app.core.dependencies import get_current_user
from app.models.app_user_model import AppUserModel
from app.schemas.app_user_schema import AppUserResponse
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AppUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea siempre un usuario con rol CLIENTE y estado ACTIVO.",
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    endpoint = f"{request.method} {request.url.path}"[:255]
    return auth_controller.register_user(db, payload, endpoint=endpoint)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description="Autentica credenciales y genera un token JWT Bearer.",
)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_controller.login_user(db, payload)


@router.get(
    "/me",
    response_model=AppUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario autenticado",
    description="Devuelve la información del usuario correspondiente al token Bearer presentado.",
)
def me(
    current_user: Annotated[AppUserModel, Depends(get_current_user)],
):
    return auth_controller.get_current_user_profile(current_user)
