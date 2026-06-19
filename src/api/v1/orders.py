from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.order import OrderCreateRequest, OrderResponse, OrderItemResponse, AddressResponse, PaymentMethodResponse, StatusHistoryItem
from src.services.checkout_service import process_checkout, CartValidationError
from src.services.b2b_client import B2BUnavailableError, ReserveFailedError
from src.models.order import OrderItem

router = APIRouter(prefix="/api/v1", tags=["B2C: Orders"])

def get_current_buyer(authorization: str = Header(..., alias="Authorization")) -> str:
    """
    Извлечение buyer_id из JWT-токена.
    В реальной системе здесь парсинг JWT. Для тестов возвращаем мок.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Требуется Bearer токен"})
    # В production: декодирование JWT и извлечение sub (buyer_id)
    # Для тестов: мок buyer_id
    return "buyer-001"

@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    buyer_id: str = Depends(get_current_buyer)
):
    try:
        result = process_checkout(db, payload, idempotency_key, buyer_id)
        order = result["order"]
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        return OrderResponse(
            id=order.id,
            number=order.number,
            buyer_id=order.buyer_id,
            status=order.status.value,
            status_history=[StatusHistoryItem(**h) for h in order.status_history],
            items=[
                OrderItemResponse(
                    sku_id=item.sku_id,
                    product_id=item.product_id,
                    name=item.name,
                    sku_code=item.sku_code,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    image_url=item.image_url
                )
                for item in order_items
            ],
            subtotal=order.subtotal,
            delivery_cost=order.delivery_cost,
            total=order.total,
            address=AddressResponse(**order.address_snapshot),
            payment_method=PaymentMethodResponse(**order.payment_method_snapshot),
            comment=order.comment,
            cancel_reason=order.cancel_reason,
            created_at=order.created_at,
            paid_at=order.paid_at,
            delivered_at=order.delivered_at
        )
    except B2BUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "B2B or Cart service unavailable"}
        )
    except ReserveFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RESERVE_FAILED",
                "message": "One or more items could not be reserved",
                "failed_items": e.failed_items
            }
        )
    except CartValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CART_INVALID", "message": str(e)}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(e)}
        )