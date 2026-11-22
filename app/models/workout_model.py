from enum import Enum as PythonEnum

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base
from app.models.app_user_model import AppUserModel


class ExerciseType(str, PythonEnum):
    DYNAMIC = "DINAMICO"
    ISOMETRIC = "ISOMETRICO"


class WorkoutModel(Base):
    __tablename__ = "workout"
    __table_args__ = (
        UniqueConstraint("name", name="uq_workout_name"),
        CheckConstraint("NOT allow_negative_ballast OR is_bodyweight", name="chk_workout_negative_ballast"),
        Index("idx_workout_created_by", "created_by"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, name="exercise_type", values_callable=lambda members: [member.value for member in members], validate_strings=True),
        nullable=False,
    )
    is_bodyweight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    allow_positive_ballast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    allow_negative_ballast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    state: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(AppUserModel.__table__.c.id, name="fk_workout_creator", ondelete="SET NULL"),
        nullable=True,
    )
