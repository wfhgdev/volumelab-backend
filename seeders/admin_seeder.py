import os

from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus

load_dotenv()

DEFAULT_ADMIN_EMAIL = "admin@volumelab.com"
DEFAULT_ADMIN_PASSWORD = "Admin1234!"


def seed_admin(db: Session) -> AppUserModel | None:
    """Crea el primer usuario administrador si no existe todavía por email."""
    email = (os.getenv("ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).strip()
    password = os.getenv("ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD

    existing = (
        db.query(AppUserModel)
        .filter(func.lower(AppUserModel.email) == email.lower())
        .first()
    )
    if existing is not None:
        return None

    admin = AppUserModel(
        email=email,
        password_hash=hash_password(password),
        name="Administrador",
        lastname="VolumeLab",
        role=RoleUser.ADMIN,
        status=UserStatus.ACTIVO,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
