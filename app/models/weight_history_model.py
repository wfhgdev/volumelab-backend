from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    Table,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base

try:
    from app.models import app_user_model as _app_user_model  # noqa: F401
except ImportError:
    if "app_user" not in Base.metadata.tables:
        Table(
            "app_user",
            Base.metadata,
            Column("id", BigInteger, primary_key=True),
        )


class WeightHistoryModel(Base):
    __tablename__ = "weight_history"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="chk_weight_kg"),
        Index("idx_weight_history_user_date", "user_id", desc("created_at")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("app_user.id", name="fk_weight_history_user", ondelete="CASCADE"),
        nullable=False,
    )
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.current_timestamp(),
    )
