from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash_helper = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Calcula el hash seguro de una contraseña usando argon2."""
    return _password_hash_helper.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash almacenado."""
    return _password_hash_helper.verify(plain_password, hashed_password)


def create_access_token(user_id: int | str, role: str) -> str:
    """
    Genera un token JWT firmado con HS256.
    Claims: sub (string), role, iat, exp.
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": str(getattr(role, "value", role)),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un token JWT.
    Lanza jwt.ExpiredSignatureError si ha expirado o jwt.PyJWTError si es inválido.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
