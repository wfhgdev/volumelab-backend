import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Table,
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


class AuditAction(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"


class AuditModel(Base):
    """
    Modelo ORM para la entidad 'audit' según el esquema canónico v4 de volumelab.

    Columnas exactas de PostgreSQL:
    - id, user_id (FK ON DELETE CASCADE — RGPD art. 17), entity, record_id,
      action (audit_action ENUM), endpoint, created_at.
    """

    __tablename__ = "audit"
    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_entity_record", "entity", "record_id"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("app_user.id", name="fk_audit_user", ondelete="CASCADE"),
        nullable=True,
    )
    entity: Mapped[str] = mapped_column(String(60), nullable=False)
    record_id: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.current_timestamp(),
    )
