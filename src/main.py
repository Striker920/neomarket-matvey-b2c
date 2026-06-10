from fastapi import FastAPI
from src.api.v1.orders import router as orders_router
from src.models.base import Base
from src.models.order import Order, OrderItem  # <-- ВАЖНО: импортируем для create_all
from src.database import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2C Orders (Matvey)")
app.include_router(orders_router)