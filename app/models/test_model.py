from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database_connection import Base


class TestModel(Base):
    __tablename__ = "test"
    __table_args__ = {"extend_existing": True}
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    test_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    test_type: Mapped[str] = mapped_column(String)

