from fastapi import APIRouter, Depends, HTTPException, Header
from src.schemas.event import B2BEvent
from src.services.event_service import EventService
from src.database import get_db
from src.config import settings
from sqlalchemy.orm import Session
from typing import Optional


# ✅ ИСПРАВЛЕНО: prefix="/api/v1/b2b" вместо "/api/v1/events"
router = APIRouter(prefix="/api/v1/b2b", tags=["B2B Events"])


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2B_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-Service-Key"}
        )
    return True


# ✅ ИСПРАВЛЕНО: endpoint="/events" вместо "/product"
# Итоговый путь: POST /api/v1/b2b/events (по b2c/openapi.yaml:758)
@router.post("/events")
def handle_product_event(
    payload: B2BEvent,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    """
    Приём событий от B2B: PRODUCT_BLOCKED, PRODUCT_DELETED, SKU_OUT_OF_STOCK.
    Путь: POST /api/v1/b2b/events (по b2c/openapi.yaml:758)
    """
    service = EventService(db)
    result = service.handle_product_event(payload.model_dump())

    if result.get("status") == "duplicate":
        return {"accepted": True}

    return {"accepted": True}