import uuid
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.order import Order, OrderItem, OrderStatus
from src.schemas.order import OrderCreateRequest
from src.services.b2b_client import b2b_client, B2BUnavailableError, ReserveFailedError

class CartValidationError(Exception): pass

def _fetch_sku_details(sku_ids: List[str]) -> Dict[str, dict]:
    """
    Получение деталей SKU (цены, названия) ДО резервирования.
    В реальности: вызов B2B GET /api/v1/products?ids=...
    """
    mock_db = {
        "sku-001": {"unit_price": 299900, "product_id": "prod-001", "product_title": "Test Product", "sku_name": "Black, L", "sku_code": "TST-BLK-L", "image_url": "https://example.com/img.jpg"},
        "sku-002": {"unit_price": 150000, "product_id": "prod-002", "product_title": "Another Product", "sku_name": "Red, M", "sku_code": "ANT-RED-M"},
        "sku-003": {"unit_price": 150000, "product_id": "prod-003", "product_title": "Idem", "sku_name": "Red"},
    }
    return {sku_id: mock_db.get(sku_id, {}) for sku_id in sku_ids}

def process_checkout(db: Session, payload: OrderCreateRequest, idempotency_key: str, buyer_id: str) -> dict:
    existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
    if existing_order:
        return {"status": "idempotent", "order": existing_order}

    order_id = str(uuid.uuid4())

    sku_ids = [item.sku_id for item in payload.items]
    sku_details = _fetch_sku_details(sku_ids)

    items_for_reserve = []
    order_items_data = []
    subtotal = 0

    for item in payload.items:
        info = sku_details.get(item.sku_id)
        if not info or not info.get("unit_price"):
            raise ValueError(f"Не удалось получить информацию о SKU {item.sku_id}")

        unit_price = info["unit_price"]
        line_total = unit_price * item.quantity
        subtotal += line_total

        items_for_reserve.append({"sku_id": item.sku_id, "quantity": item.quantity})
        order_items_data.append({
            "sku_id": item.sku_id,
            "product_id": info.get("product_id", "unknown"),
            "name": f"{info.get('product_title', 'Product')} - {info.get('sku_name', 'SKU')}",
            "sku_code": info.get("sku_code"),
            "quantity": item.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "image_url": info.get("image_url")
        })

    try:
        reserve_result = b2b_client.reserve_inventory(order_id, items_for_reserve, idempotency_key)
    except (B2BUnavailableError, ReserveFailedError):
        raise

    address = _get_address(payload.address_id, buyer_id)
    payment_method = _get_payment_method(payload.payment_method_id, buyer_id)
    delivery_cost = 0
    total = subtotal + delivery_cost
    order_number = f"NM-2026-{order_id[:8].upper()}"
    now = datetime.utcnow().isoformat()

    order = Order(
        id=order_id, number=order_number, buyer_id=buyer_id, status=OrderStatus.PAID,
        idempotency_key=idempotency_key, address_snapshot=address, payment_method_snapshot=payment_method,
        subtotal=subtotal, delivery_cost=delivery_cost, total=total, comment=payload.comment,
        status_history=[
            {"status": OrderStatus.CREATED.value, "changed_at": now, "reason": None},
            {"status": OrderStatus.PAID.value, "changed_at": now, "reason": "Мок-оплата"}
        ],
        paid_at=datetime.utcnow()
    )
    db.add(order)
    db.flush()

    for item_data in order_items_data:
        db.add(OrderItem(id=str(uuid.uuid4()), order_id=order_id, **item_data))

    try:
        db.commit()
        db.refresh(order)
    except IntegrityError:
        db.rollback()
        existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
        if existing_order:
            return {"status": "idempotent", "order": existing_order}
        raise

    return {"status": "created", "order": order}

def _get_address(address_id: str, buyer_id: str) -> dict:
    return {
        "id": address_id, "country": "Россия", "city": "Москва", "street": "ул. Тестовая", 
        "building": "1", "apartment": "10", "postal_code": "101000", "recipient_name": "Иван Иванов", 
        "recipient_phone": "+79991234567", "created_at": datetime.utcnow().isoformat()
    }

def _get_payment_method(method_id: str, buyer_id: str) -> dict:
    return {
        "id": method_id, "type": "CARD", "card_last4": "1234", "card_brand": "VISA", 
        "is_default": True, "created_at": datetime.utcnow().isoformat()
    }