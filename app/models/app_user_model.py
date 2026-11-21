import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Enum, Identity, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base


class UserGender(str, enum.Enum):
    HOMBRE = "HOMBRE"
    MUJER = "MUJER"
    PREFIERO_NO_DECIR = "PREFIERO NO DECIR"


class UserStatus(str, enum.Enum):
    ACTIVO = "ACTIVO"
    BLOQUEADO = "BLOQUEADO"


class RoleUser(str, enum.Enum):
    ADMIN = "ADMIN"
    CLIENTE = "CLIENTE"


class AppUserModel(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("birth_date IS NULL OR birth_date <= CURRENT_DATE", name="chk_user_birth_date"),
        CheckConstraint("height_cm IS NULL OR height_cm BETWEEN 50 AND 300", name="chk_user_height"),
        Index("uq_app_user_email", text("LOWER(email)"), unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    lastname: Mapped[str | None] = mapped_column(String(150), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[UserGender | None] = mapped_column(
        Enum(
            UserGender,
            name="user_gender",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=True,
    )
    role: Mapped[RoleUser] = mapped_column(
        Enum(
            RoleUser,
            name="role_user",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=RoleUser.CLIENTE,
        server_default=text("'CLIENTE'::role_user"),
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=UserStatus.ACTIVO,
        server_default=text("'ACTIVO'::user_status"),
    )
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.current_timestamp(),
    )
