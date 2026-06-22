from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Типы событий от B2B."""
    PRODUCT_BLOCKED = "PRODUCT_BLOCKED"
    PRODUCT_DELETED = "PRODUCT_DELETED"
    SKU_OUT_OF_STOCK = "SKU_OUT_OF_STOCK"
    PRICE_CHANGED = "PRICE_CHANGED"


class EventProductRef(BaseModel):
    """Payload для PRODUCT_BLOCKED / PRODUCT_DELETED."""
    product_id: str
    reason: Optional[str] = None


class EventSkuStock(BaseModel):
    """Payload для SKU_OUT_OF_STOCK."""
    product_id: str
    sku_ids: List[str]


class EventPriceChanged(BaseModel):
    """Payload для PRICE_CHANGED."""
    product_id: str
    sku_ids: List[str]
    new_price: int


# ✅ ИСПРАВЛЕНО: полная переработка схемы по b2c/openapi.yaml:1370-1389
class B2BEvent(BaseModel):
    """
    Схема события от B2B.
    
    Обязательные поля:
    - event_type: тип события
    - idempotency_key: ключ идемпотентности
    - occurred_at: время возникновения
    - payload: данные события (oneOf EventProductRef / EventSkuStock / EventPriceChanged)
    """
    # ✅ ИСПРАВЛЕНО: event_type вместо event
    event_type: EventType
    
    # ✅ ДОБАВЛЕНО: idempotency_key (обязательное)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    
    # ✅ ДОБАВЛЕНО: occurred_at (обязательное)
    occurred_at: datetime
    
    # ✅ ИСПРАВЛЕНО: payload вместо плоских полей
    payload: Union[EventProductRef, EventSkuStock, EventPriceChanged]


# Для обратной совместимости (если EventService использует ProductEventRequest)
ProductEventRequest = B2BEvent