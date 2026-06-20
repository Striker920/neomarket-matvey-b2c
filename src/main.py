from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from src.api.v1.orders import router as orders_router
from src.models.base import Base
from src.models.order import Order, OrderItem
from src.database import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2C Orders (Matvey)")
app.include_router(orders_router)


# <-- ДОБАВЛЕНО: глобальный exception handler для плоского {code, message}
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Переупаковка HTTPException.detail в плоский {code, message} согласно b2c openapi:870-879"""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail  # плоский {code, message}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "ERROR", "message": str(exc.detail)}
    )