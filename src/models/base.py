import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ProductStatus(str, Enum):
    DRAFT = "DRAFT"
    ON_MODERATION = "ON_MODERATION"
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"
    ARCHIVED = "ARCHIVED"

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    block_reason = Column(String(500), nullable=True)
    blocking_reason_id = Column(String(36), nullable=True)
    field_reports = Column(JSON, nullable=True)
