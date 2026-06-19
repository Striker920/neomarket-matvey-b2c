import httpx
from typing import List, Dict, Any
from src.core.config import settings

class CartClientError(Exception): pass
class CartUnavailableError(CartClientError): pass

class CartClient:
    def __init__(self, base_url: str = None, timeout: float = 5.0):
        self.base_url = base_url or settings.CART_SERVICE_URL
        self.timeout = timeout

    def get_cart(self, buyer_id: str) -> List[Dict[str, Any]]:
        """
        Получение корзины покупателя через HTTP-вызов к Cart Service.
        Путь: GET /api/v1/cart/{buyer_id}
        Response: {"items": [{"sku_id": "...", "quantity": ...}, ...]}
        """
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/cart/{buyer_id}",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except httpx.RequestError as e:
            raise CartUnavailableError(f"Cannot fetch cart: {str(e)}")

cart_client = CartClient()