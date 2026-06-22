import pytest
from unittest.mock import patch, MagicMock

MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15",
    "slug": "iphone-15",
    "description": "Smartphone",
    "status": "MODERATED",
    "category_id": "cat-1",
    "images": [{"url": "/s3/iphone15.jpg", "ordering": 0}],
    "characteristics": [
        {"name": "Бренд", "value": "Apple"},
        {"name": "Цвет", "value": "Чёрный"}
    ],
    "skus": [
        {
            "id": "sku-1",
            "name": "256GB Black",
            "price": 12999000,
            "discount": 0,
            "image": "/s3/iphone15-black.jpg",
            "active_quantity": 10,
            "characteristics": []
        }
    ]
}


class TestCart:

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_add_sku_increments_quantity_if_already_in_cart(self, mock_get_products, client, valid_jwt):
        """Repeat add of same SKU increments quantity"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        response1 = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 2},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 3},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response2.status_code == 200
        
        # ✅ ИСПРАВЛЕНО: теперь POST возвращает CartResponse
        data = response2.json()
        assert data["items_count"] == 1
        
        # Находим позицию по sku_id
        item = next((i for i in data["items"] if i["sku_id"] == "sku-1"), None)
        assert item is not None
        assert item["quantity"] == 5  # 2 + 3
        
        # Проверяем новые обязательные поля
        assert "name" in item
        assert "unit_price" in item
        assert "line_total" in item
        assert "available_quantity" in item
        assert "is_available" in item

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_get_cart_enriched_with_b2b_data(self, mock_get_products, client, valid_jwt):
        """GET /cart returns enriched data from B2B"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        
        # ✅ ИСПРАВЛЕНО: title → name
        assert data["items"][0]["name"] == "iPhone 15"
        assert data["items"][0]["sku_id"] == "sku-1"
        assert data["items"][0]["quantity"] == 1
        
        # ✅ Проверяем новые обязательные поля
        assert data["items"][0]["unit_price"] == 12999000
        assert data["items"][0]["line_total"] == 12999000  # 1 * 12999000
        assert data["items"][0]["available_quantity"] == 10
        assert data["items"][0]["is_available"] is True
        
        # ✅ Проверяем новые поля CartResponse
        assert data["items_count"] == 1
        assert data["subtotal"] == 12999000
        assert data["is_valid"] is True

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_unavailable_sku_shown_with_reason(self, mock_get_products, client, valid_jwt):
        """Unavailable SKU shown with unavailable_reason"""
        product = MOCK_B2B_PRODUCT.copy()
        product["skus"] = [
            {
                "id": "sku-1",
                "name": "256GB Black",
                "price": 12999000,
                "active_quantity": 0,  # ❌ Нет в наличии
                "image": "/s3/iphone15-black.jpg",
                "characteristics": []
            }
        ]
        mock_get_products.return_value = {"items": [product], "total_count": 1}

        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        
        # ✅ ИСПРАВЛЕНО: available → is_available
        assert data["items"][0]["is_available"] is False
        assert data["items"][0]["unavailable_reason"] == "OUT_OF_STOCK"
        
        # Недоступные позиции НЕ входят в subtotal
        assert data["subtotal"] == 0
        assert data["is_valid"] is False
        assert data["summary"]["unavailable_count"] == 1

    def test_update_quantity(self, client, valid_jwt):
        """Update cart item quantity by SKU ID"""
        add_response = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        
        sku_id = "sku-1"

        response = client.patch(
            f"/api/v1/cart/items/{sku_id}",
            json={"quantity": 5},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        
        # ✅ ИСПРАВЛЕНО: теперь PATCH возвращает CartResponse
        data = response.json()
        assert data["items_count"] == 1
        
        # Находим позицию по sku_id
        item = next((i for i in data["items"] if i["sku_id"] == sku_id), None)
        assert item is not None
        assert item["quantity"] == 5

    def test_guest_cart_works_with_session_id(self, client):
        """Guest cart works with X-Session-Id header"""
        response = client.get(
            "/api/v1/cart",
            headers={"X-Session-Id": "test-session-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["items_count"] == 0

    def test_missing_identity_returns_400(self, client):
        """Missing both Authorization and X-Session-Id returns 400"""
        response = client.get("/api/v1/cart")
        assert response.status_code == 400

    def test_remove_item(self, client, valid_jwt):
        """Remove item from cart by SKU ID"""
        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.delete(
            "/api/v1/cart/items/sku-1",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items_count"] == 0

    def test_clear_cart(self, client, valid_jwt):
        """Clear entire cart"""
        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.delete(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_guest_cart_merged_on_login(self, client, valid_jwt):
        """Guest cart merged with auth cart on login"""
        session_id = "test-session-456"

        # Добавляем в гостевую корзину
        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 2},
            headers={"X-Session-Id": session_id}
        )

        # Добавляем в авторизованную корзину
        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 3},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        # Merge
        response = client.post(
            "/api/v1/cart/merge",
            headers={
                "X-Session-Id": session_id,
                "Authorization": f"Bearer {valid_jwt}"
            }
        )

        assert response.status_code == 200
        data = response.json()
        
        # Проверяем, что взялось MAX(2, 3) = 3
        item = next((i for i in data["items"] if i["sku_id"] == "sku-1"), None)
        assert item is not None
        assert item["quantity"] == 3