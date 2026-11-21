from datetime import datetime, date
from typing import Optional
from sqlalchemy import BigInteger, Integer, String, Date as SQLDate, DateTime, Identity, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database_connection import Base


class UserModel(Base):
    __tablename__ = "app_user"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
        autoincrement=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    lastname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(SQLDate, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="CLIENTE", server_default="CLIENTE", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVO", server_default="ACTIVO", nullable=False)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
