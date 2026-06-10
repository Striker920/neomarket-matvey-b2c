import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base

class OrderStatus(str, Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    ASSEMBLING = "ASSEMBLING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    CANCEL_PENDING = "CANCEL_PENDING"

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    number = Column(String(50), nullable=True)
    buyer_id = Column(String(36), nullable=False, index=True)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    address_snapshot = Column(JSON, nullable=False)
    payment_method_snapshot = Column(JSON, nullable=False)
    subtotal = Column(Integer, nullable=False)
    delivery_cost = Column(Integer, default=0)
    total = Column(Integer, nullable=False)
    comment = Column(String(1000), nullable=True)
    cancel_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    status_history = Column(JSON, default=list)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    sku_id = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    sku_code = Column(String(64), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    line_total = Column(Integer, nullable=False)
    image_url = Column(String(512), nullable=True)
    order = relationship("Order", back_populates="items")