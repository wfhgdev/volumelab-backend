from datetime import date
from enum import Enum
from sqlalchemy import BigInteger, Integer, String, Date as SQLDate, ForeignKey, CheckConstraint, Enum as SQLEnum, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database_connection import Base
from app.models.app_user_model import AppUserModel


class MesocycleStatus(str, Enum):
    PLANIFICADO = "PLANIFICADO"
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"


class MesocycleModel(Base):
    __tablename__ = "mesocycle"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_mesocycle_dates"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(SQLDate, nullable=False)
    end_date: Mapped[date] = mapped_column(SQLDate, nullable=False)
    status: Mapped[MesocycleStatus] = mapped_column(
        SQLEnum(
            MesocycleStatus,
            name="mesocycle_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
        default=MesocycleStatus.PLANIFICADO,
        server_default="PLANIFICADO"
    )

    user: Mapped["AppUserModel"] = relationship("AppUserModel", backref="mesocycles", lazy="select")
