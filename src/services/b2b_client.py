import httpx
from typing import List, Dict, Any
from src.core.config import settings

class B2BClientError(Exception): pass
class B2BUnavailableError(B2BClientError): pass

class ReserveFailedError(B2BClientError):
    def __init__(self, failed_items: List[Dict[str, str]]):
        self.failed_items = failed_items
        super().__init__(f"Reserve failed: {failed_items}")

class B2BClient:
    def __init__(self, base_url: str = None, timeout: float = 5.0):
        self.base_url = base_url or settings.B2B_SERVICE_URL
        self.timeout = timeout

    def reserve_inventory(self, order_id: str, items: List[Dict[str, Any]], idempotency_key: str) -> Dict[str, Any]:
        """
        Резервирование товаров через B2B.
        Путь: POST /api/v1/inventory/reserve
        Payload: {idempotency_key, order_id, items}
        Response: {order_id, status: RESERVED, reserved_at}
        """
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/inventory/reserve",  # <-- Правильный путь
                json={
                    "order_id": order_id,       # <-- Обязательное поле
                    "items": items,
                    "idempotency_key": idempotency_key
                },
                headers={
                    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
            if response.status_code == 503:
                raise B2BUnavailableError("B2B service unavailable")
            if response.status_code == 409:
                data = response.json()
                raise ReserveFailedError(data.get("failed_items", []))
            if response.status_code >= 500:
                raise B2BUnavailableError(f"B2B service error: {response.status_code}")
            if response.status_code != 200:
                raise B2BClientError(f"B2B returned {response.status_code}")
            
            # Реальный ответ B2B: {order_id, status: RESERVED, reserved_at}
            return response.json()
        except httpx.RequestError as e:
            raise B2BUnavailableError(f"Cannot connect to B2B: {str(e)}")

    def get_sku_details_batch(self, sku_ids: List[str]) -> Dict[str, dict]:
        """
        Получение актуальных цен и деталей SKU через публичный B2B-эндпоинт.
        Путь: POST /api/v1/public/products/batch (с X-Service-Key)
        """
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/public/products/batch",
                json={"sku_ids": sku_ids},
                headers={
                    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return {item["sku_id"]: item for item in data.get("items", [])}
        except httpx.RequestError as e:
            raise B2BUnavailableError(f"Cannot fetch SKU details from B2B: {str(e)}")

b2b_client = B2BClient()