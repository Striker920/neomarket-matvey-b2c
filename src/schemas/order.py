from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class OrderItemRequest(BaseModel):
    sku_id: str
    quantity: int = Field(..., gt=0)

class OrderItemSnapshot(BaseModel):
    sku_id: str
    quantity: int = Field(..., gt=0)
    unit_price: int = Field(..., ge=0)

class OrderCreateRequest(BaseModel):
    address_id: str = Field(..., description="ID адреса доставки")
    payment_method_id: str = Field(..., description="ID платёжного метода")
    comment: Optional[str] = Field(None, max_length=1000)
    items: List[OrderItemRequest] = Field(..., description="Список товаров для заказа")
    items_snapshot: Optional[List[OrderItemSnapshot]] = Field(None, description="Опциональный снапшот для валидации")

class OrderItemResponse(BaseModel):
    sku_id: str
    product_id: str
    name: str
    sku_code: Optional[str] = None
    quantity: int
    unit_price: int
    line_total: int
    image_url: Optional[str] = None

class AddressResponse(BaseModel):
    id: str
    country: str
    city: str
    street: str
    building: str
    apartment: Optional[str] = None
    postal_code: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    created_at: datetime

class PaymentMethodResponse(BaseModel):
    id: str
    type: str
    card_last4: Optional[str] = None
    card_brand: Optional[str] = None
    is_default: bool = False
    created_at: datetime

class StatusHistoryItem(BaseModel):
    status: str
    changed_at: datetime
    reason: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    number: Optional[str] = None
    buyer_id: str
    status: str
    status_history: List[StatusHistoryItem] = []
    items: List[OrderItemResponse]
    subtotal: int
    delivery_cost: int = 0
    total: int
    address: AddressResponse
    payment_method: PaymentMethodResponse
    comment: Optional[str] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None