from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date as SQLDate,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Identity,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database_connection import Base
from app.models.app_user_model import AppUserModel
from app.models.training_week_model import TrainingWeekModel


class SessionStatus(str, Enum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class WorkoutSessionModel(Base):
    __tablename__ = "workout_session"
    __table_args__ = (
        CheckConstraint("(status = 'CERRADO') = (closed_at IS NOT NULL)", name="chk_session_closed"),
        CheckConstraint("current_bodyweight_kg IS NULL OR current_bodyweight_kg > 0", name="chk_session_snapshot"),
        Index("idx_workout_session_user_date", "user_id", text("session_date DESC")),
        Index("idx_workout_session_week", "week_id"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("training_week.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    session_date: Mapped[date] = mapped_column(SQLDate, nullable=False)
    current_bodyweight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(
            SessionStatus,
            name="session_status",
            create_type=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SessionStatus.ABIERTO,
        server_default="ABIERTO",
    )

    user: Mapped["AppUserModel"] = relationship("AppUserModel", backref="workout_sessions", lazy="select")
    week: Mapped["TrainingWeekModel"] = relationship("TrainingWeekModel", backref="workout_sessions", lazy="select")
