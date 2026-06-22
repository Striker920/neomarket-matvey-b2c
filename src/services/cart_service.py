from sqlalchemy.orm import Session
from src.models.cart import CartItem
from src.services.b2b_client import b2b_client
from src.schemas.cart import CartItemResponse, CartResponse, CartSummary
import uuid
from datetime import datetime


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def _get_identity(self, user_id: str = None, session_id: str = None):
        if user_id:
            return {"user_id": user_id, "session_id": None}
        if session_id:
            return {"user_id": None, "session_id": session_id}
        return None

    def add_item(self, sku_id: str, quantity: int, user_id: str = None, session_id: str = None) -> dict:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return {"error": "MISSING_IDENTITY"}

        query = self.db.query(CartItem).filter(
            CartItem.sku_id == sku_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        )

        existing = query.first()

        if existing:
            existing.quantity += quantity
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return {"status": "updated", "item_id": existing.id, "quantity": existing.quantity}

        item = CartItem(
            id=str(uuid.uuid4()),
            user_id=identity["user_id"],
            session_id=identity["session_id"],
            sku_id=sku_id,
            quantity=quantity
        )
        self.db.add(item)
        self.db.commit()

        return {"status": "created", "item_id": item.id, "quantity": item.quantity}

    def update_item(self, sku_id: str, quantity: int, user_id: str = None, session_id: str = None) -> dict:
        """Обновление количества товара по SKU ID."""
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return {"error": "MISSING_IDENTITY"}

        item = self.db.query(CartItem).filter(
            CartItem.sku_id == sku_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).first()

        if not item:
            return {"error": "NOT_FOUND"}

        item.quantity = quantity
        item.updated_at = datetime.utcnow()
        self.db.commit()

        return {"status": "updated", "item_id": item.id, "quantity": item.quantity}

    def remove_item(self, sku_id: str, user_id: str = None, session_id: str = None) -> bool:
        """Удаление товара из корзины по SKU ID."""
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return False

        item = self.db.query(CartItem).filter(
            CartItem.sku_id == sku_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).first()

        if item:
            self.db.delete(item)
            self.db.commit()
            return True

        return False

    def clear_cart(self, user_id: str = None, session_id: str = None) -> bool:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return False

        items = self.db.query(CartItem).filter(
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).all()

        for item in items:
            self.db.delete(item)

        self.db.commit()
        return True

    # ✅ ИСПРАВЛЕНО: возвращает CartResponse с обязательными полями
    def get_cart(self, user_id: str = None, session_id: str = None) -> CartResponse:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return CartResponse(
                items=[],
                summary=CartSummary(),
                items_count=0,
                subtotal=0,
                is_valid=True,
            )

        items = self.db.query(CartItem).filter(
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).all()

        if not items:
            return CartResponse(
                items=[],
                summary=CartSummary(),
                items_count=0,
                subtotal=0,
                is_valid=True,
            )

        sku_ids = [item.sku_id for item in items]

        try:
            # ✅ ИСПРАВЛЕНО: вызов публичного endpoint
            b2b_data = b2b_client.get_products(limit=100, offset=0, ids=",".join(sku_ids))
            b2b_products = {p["id"]: p for p in b2b_data.get("items", [])}
        except Exception:
            b2b_products = {}

        enriched_items = []
        total_amount = 0
        total_items = 0
        unavailable_count = 0

        for item in items:
            product = None
            sku_data = None

            for pid, pdata in b2b_products.items():
                for s in pdata.get("skus", []):
                    if s.get("id") == item.sku_id:
                        product = pdata
                        sku_data = s
                        break
                if product:
                    break

            if not product or not sku_data:
                enriched_items.append(CartItemResponse(
                    id=item.id,
                    sku_id=item.sku_id,
                    product_id=item.sku_id,
                    name="Product not found",
                    quantity=item.quantity,
                    unit_price=0,
                    line_total=0,
                    available_quantity=0,
                    is_available=False,
                    unavailable_reason="PRODUCT_DELETED",
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                ))
                unavailable_count += 1
                continue

            active_qty = sku_data.get("active_quantity", 0)
            available = active_qty >= item.quantity
            unit_price = sku_data.get("price", 0)
            line_total = unit_price * item.quantity if available else 0

            enriched_items.append(CartItemResponse(
                id=item.id,
                sku_id=item.sku_id,
                product_id=product.get("id"),
                name=product.get("title"),
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
                available_quantity=active_qty,
                is_available=available,
                image=sku_data.get("image"),
                unavailable_reason="OUT_OF_STOCK" if not available else None,
                created_at=item.created_at,
                updated_at=item.updated_at,
            ))

            if available:
                total_amount += line_total
                total_items += item.quantity
            else:
                unavailable_count += 1

        # ✅ ИСПРАВЛЕНО: возвращаем CartResponse с обязательными полями
        return CartResponse(
            items=enriched_items,
            summary=CartSummary(
                total_amount=total_amount,
                total_items=total_items,
                unavailable_count=unavailable_count,
                checkout_ready=unavailable_count == 0,
            ),
            items_count=len(enriched_items),
            subtotal=total_amount,
            is_valid=unavailable_count == 0,
        )

    def merge_guest_cart(self, user_id: str, session_id: str) -> dict:
        """
        US-CART-03: Слияние гостевой корзины с авторизованной.
        При конфликте берёт MAX(guest, auth) quantity.
        """
        guest_items = self.db.query(CartItem).filter(
            CartItem.session_id == session_id,
            CartItem.user_id == None
        ).all()

        for guest_item in guest_items:
            existing = self.db.query(CartItem).filter(
                CartItem.user_id == user_id,
                CartItem.sku_id == guest_item.sku_id
            ).first()

            if existing:
                # ✅ При конфликте берём MAX(guest, auth)
                existing.quantity = max(existing.quantity, guest_item.quantity)
                self.db.delete(guest_item)
            else:
                guest_item.user_id = user_id
                guest_item.session_id = None

        self.db.commit()
        return {"status": "merged"}