from sqlalchemy import ForeignKey, Identity, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base
from app.models.app_user_model import AppUserModel


class MuscleGroupModel(Base):
    __tablename__ = "muscle_group"
    __table_args__ = (
        UniqueConstraint("name", name="uq_muscle_group_name"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            AppUserModel.__table__.c.id,
            name="fk_muscle_group_creator",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
