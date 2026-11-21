from datetime import date
from sqlalchemy import BigInteger, Integer, Date as SQLDate, ForeignKey, CheckConstraint, UniqueConstraint, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database_connection import Base
from app.models.mesocycle_model import MesocycleModel


class TrainingWeekModel(Base):
    __tablename__ = "training_week"
    __table_args__ = (
        CheckConstraint("week_order >= 1", name="chk_training_week_order"),
        CheckConstraint("end_date >= start_date", name="chk_training_week_dates"),
        UniqueConstraint("mesocycle_id", "week_order", name="uq_training_week_order"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
        autoincrement=True
    )
    mesocycle_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("mesocycle.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    week_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(SQLDate, nullable=False)
    end_date: Mapped[date] = mapped_column(SQLDate, nullable=False)

    mesocycle: Mapped["MesocycleModel"] = relationship("MesocycleModel", backref="training_weeks", lazy="select")
