import uuid
import httpx
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.order import Order, OrderItem, OrderStatus
from src.schemas.order import OrderCreateRequest
from src.services.b2b_client import b2b_client, B2BUnavailableError, ReserveFailedError
from src.core.config import settings

class CartValidationError(Exception): pass

def _get_buyer_cart(buyer_id: str) -> List[Dict[str, Any]]:
    """
    Чтение корзины покупателя server-side.
    В реальной реализации здесь будет HTTP-запрос к Cart Service или чтение из БД.
    """
    # Реальная реализация:
    # response = httpx.get(f"{settings.CART_SERVICE_URL}/api/v1/carts/{buyer_id}")
    # return response.json()["items"]
    
    # Заглушка, которая переопределяется (mock) в unit-тестах
    return []

def _fetch_sku_details_from_b2b(sku_ids: List[str]) -> Dict[str, dict]:
    """Получение актуальных цен и деталей SKU через HTTP GET к B2B сервису"""
    # Реальная реализация HTTP-запроса к B2B
    response = httpx.get(
        f"{settings.B2B_SERVICE_URL}/api/v1/products",
        params={"ids": ",".join(sku_ids)},
        headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
        timeout=5.0
    )
    response.raise_for_status()
    # Ожидаемый формат ответа B2B: {"items": [{"sku_id": "...", "unit_price": 100, ...}]}
    data = response.json()
    return {item["sku_id"]: item for item in data.get("items", [])}

def process_checkout(db: Session, payload: OrderCreateRequest, idempotency_key: str, buyer_id: str) -> dict:
    existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
    if existing_order:
        return {"status": "idempotent", "order": existing_order}

    # 1. Читаем корзину server-side
    cart_items = _get_buyer_cart(buyer_id)
    if not cart_items:
        raise CartValidationError("Корзина пуста")

    # 2. Валидация items_snapshot (если передан)
    if payload.items_snapshot:
        snapshot_dict = {item.sku_id: item.quantity for item in payload.items_snapshot}
        for item in cart_items:
            if snapshot_dict.get(item["sku_id"]) != item["quantity"]:
                raise CartValidationError("Расхождение с снапшотом корзины")

    order_id = str(uuid.uuid4())
    sku_ids = [item["sku_id"] for item in cart_items]

    # 3. Получаем актуальные цены через HTTP GET к B2B
    sku_details = _fetch_sku_details_from_b2b(sku_ids)

    items_for_reserve = []
    order_items_data = []
    subtotal = 0

    for item in cart_items:
        info = sku_details.get(item["sku_id"])
        if not info or "unit_price" not in info:
            raise ValueError(f"Не удалось получить информацию о SKU {item['sku_id']}")

        unit_price = info["unit_price"]
        quantity = item["quantity"]
        line_total = unit_price * quantity
        subtotal += line_total

        items_for_reserve.append({"sku_id": item["sku_id"], "quantity": quantity})
        order_items_data.append({
            "sku_id": item["sku_id"],
            "product_id": info.get("product_id", "unknown"),
            "name": f"{info.get('product_title', 'Product')} - {info.get('sku_name', 'SKU')}",
            "sku_code": info.get("sku_code"),
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "image_url": info.get("image_url")
        })

    # 4. All-or-nothing резервирование
    try:
        b2b_client.reserve_inventory(order_id, items_for_reserve, idempotency_key)
    except (B2BUnavailableError, ReserveFailedError):
        raise

    # 5. Создание заказа
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