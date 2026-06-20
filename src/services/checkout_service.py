import uuid
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.order import Order, OrderItem, OrderStatus
from src.schemas.order import OrderCreateRequest
from src.services.b2b_client import b2b_client, B2BUnavailableError, ReserveFailedError
from src.services.cart_client import cart_client, CartUnavailableError


class CartValidationError(Exception):
    pass


def process_checkout(db: Session, payload: OrderCreateRequest, idempotency_key: str, buyer_id: str) -> dict:
    # 1. Проверка идемпотентности
    existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
    if existing_order:
        return {"status": "idempotent", "order": existing_order}

    # 2. Генерация order_id ЗАРАНЕЕ (передаётся в B2B reserve)
    order_id = str(uuid.uuid4())

    # 3. Чтение корзины server-side через HTTP-вызов к Cart Service
    try:
        cart_items = cart_client.get_cart(buyer_id)
    except CartUnavailableError:
        raise B2BUnavailableError("Cart service unavailable")
    
    if not cart_items:
        raise CartValidationError("Корзина пуста")

    # 4. Валидация items_snapshot (если передан клиентом)
    if payload.items_snapshot:
        snapshot_dict = {item.sku_id: item.quantity for item in payload.items_snapshot}
        for item in cart_items:
            expected_qty = snapshot_dict.get(item["sku_id"])
            if expected_qty is None or expected_qty != item["quantity"]:
                raise CartValidationError(
                    f"Расхождение со снапшотом корзины для SKU {item['sku_id']}"
                )

    # 5. Получение актуальных цен через HTTP-вызов к B2B (ДО резервирования!)
    sku_ids = [item["sku_id"] for item in cart_items]
    try:
        sku_details = b2b_client.get_sku_details_batch(sku_ids)
    except B2BUnavailableError:
        raise

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

    # 6. All-or-nothing резервирование через HTTP-вызов к B2B
    try:
        reserve_result = b2b_client.reserve_inventory(order_id, items_for_reserve, idempotency_key)
    except (B2BUnavailableError, ReserveFailedError):
        raise

    # 7. Создание заказа с зафиксированными ценами
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

    # <-- ИСПРАВЛЕНО: корректный блок try/except с правильными отступами
    try:
        db.commit()
        db.refresh(order)
    except IntegrityError:
        db.rollback()
        # При конфликте идемпотентности — возвращаем существующий заказ
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