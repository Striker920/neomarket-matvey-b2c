from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime, timezone
from src.database import Base


class Product(Base):
    """Товар."""
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    category_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="MODERATED")
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))