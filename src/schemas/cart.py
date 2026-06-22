from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AddToCartRequest(BaseModel):
    sku_id: str
    quantity: int = Field(..., ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


# ✅ ИСПРАВЛЕНО: переименованы поля + добавлены обязательные
class CartItemResponse(BaseModel):
    """
    Позиция корзины (по b2c/openapi.yaml:1156-1188).
    
    Required: sku_id, product_id, name, quantity, unit_price, line_total, available_quantity, is_available
    """
    id: str
    sku_id: str
    product_id: Optional[str] = None
    
    # ✅ ИСПРАВЛЕНО: name вместо title
    name: Optional[str] = None
    
    quantity: int
    
    # ✅ ИСПРАВЛЕНО: unit_price вместо price
    unit_price: Optional[int] = None
    
    # ✅ ДОБАВЛЕНО: line_total (обязательное)
    line_total: int = 0
    
    # ✅ ДОБАВЛЕНО: available_quantity (обязательное)
    available_quantity: int = 0
    
    # ✅ ИСПРАВЛЕНО: is_available вместо available
    is_available: bool = True
    
    image: Optional[str] = None
    unavailable_reason: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CartSummary(BaseModel):
    total_amount: int = 0
    total_items: int = 0
    unavailable_count: int = 0
    checkout_ready: bool = True


# ✅ ИСПРАВЛЕНО: добавлены обязательные поля
class CartResponse(BaseModel):
    """
    Ответ корзины (по b2c/openapi.yaml:1192-1208).
    
    Required: items, summary, items_count, subtotal, is_valid
    """
    items: List[CartItemResponse] = []
    summary: CartSummary = CartSummary()
    
    # ✅ ДОБАВЛЕНО: обязательные поля
    items_count: int = 0
    subtotal: int = 0
    is_valid: bool = True