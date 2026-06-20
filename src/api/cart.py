from fastapi import APIRouter, Depends, HTTPException, Header, Query
from src.schemas.cart import CartResponse, AddToCartRequest, UpdateCartItemRequest
from src.services.cart_service import CartService
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])


def get_identity(
    x_session_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    user_id = None
    session_id = None

    # ✅ ИСПРАВЛЕНО: теперь читаем ОБА идентификатора, если оба переданы
    if authorization and authorization.startswith("Bearer "):
        from jose import jwt
        from src.config import settings
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
        except Exception:
            pass

    if x_session_id:
        session_id = x_session_id

    # Если нет ни одного идентификатора — ошибка
    if not user_id and not session_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_CART_IDENTITY", "message": "Provide Authorization header or X-Session-Id"}
        )

    return {"user_id": user_id, "session_id": session_id}


@router.get("/", response_model=CartResponse)
def get_cart(
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    service = CartService(db)
    return service.get_cart(
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )


@router.post("/items", status_code=200)
def add_to_cart(
    request: AddToCartRequest,
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    service = CartService(db)
    result = service.add_item(
        sku_id=request.sku_id,
        quantity=request.quantity,
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )

    if result.get("error") == "MISSING_IDENTITY":
        raise HTTPException(status_code=400, detail={"code": "MISSING_CART_IDENTITY", "message": "No identity"})

    return result


@router.patch("/items/{sku_id}")
def update_cart_item(
    sku_id: str,
    request: UpdateCartItemRequest,
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    service = CartService(db)
    result = service.update_item(
        sku_id=sku_id,
        quantity=request.quantity,
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )

    if result.get("error") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Cart item not found"})

    return result


@router.delete("/items/{sku_id}", response_model=CartResponse)
def remove_from_cart(
    sku_id: str,
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    service = CartService(db)
    service.remove_item(
        sku_id=sku_id,
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )
    return service.get_cart(
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )


@router.delete("/", status_code=204)
def clear_cart(
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    service = CartService(db)
    service.clear_cart(
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )
    return None


@router.post("/merge", response_model=CartResponse)
def merge_cart(
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db)
):
    """
    US-CART-03: Слияние гостевой корзины с авторизованной при логине.
    Требует ОБА идентификатора: JWT (user_id) + X-Session-Id.
    """
    if not identity["user_id"]:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_USER_ID", "message": "Merge requires authenticated user"}
        )
    
    if not identity["session_id"]:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_SESSION_ID", "message": "Merge requires X-Session-Id"}
        )
    
    service = CartService(db)
    service.merge_guest_cart(
        user_id=identity["user_id"],
        session_id=identity["session_id"]
    )
    
    # Возвращаем обновлённую корзину авторизованного пользователя
    return service.get_cart(user_id=identity["user_id"])