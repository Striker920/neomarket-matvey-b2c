from sqlalchemy import Column, String, DateTime
from datetime import datetime, timezone
from src.database import Base


class Category(Base):
    """
    Категория товара.
    
    Иерархия через adjacency list (parent_id).
    """
    __tablename__ = "categories"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=True, unique=True)
    parent_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))