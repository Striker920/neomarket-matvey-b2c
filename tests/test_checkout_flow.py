import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.models.base import Base
from src.services.b2b_client import B2BUnavailableError, ReserveFailedError

engine = create_engine("sqlite:///./test_checkout.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
client = TestClient(app)

def override_get_db():
    db = TestingSessionLocal()
    try: yield db
    finally: db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

HEADERS = {"Idempotency-Key": "checkout-001", "Authorization": "Bearer mock-token"}

@patch("src.services.checkout_service.b2b_client.get_sku_details_batch")
@patch("src.services.checkout_service.cart_client.get_cart")
def test_checkout_creates_paid_order_with_fixed_prices(mock_get_cart, mock_get_sku):
    mock_get_cart.return_value = [{"sku_id": "sku-001", "quantity": 2}]
    mock_get_sku.return_value = {
        "sku-001": {"unit_price": 299900, "product_id": "prod-001", "product_title": "Test Product", "sku_name": "Black, L", "sku_code": "TST-BLK-L", "image_url": "https://example.com/img.jpg"}
    }
    
    with patch("src.services.checkout_service.b2b_client.reserve_inventory") as mock_reserve:
        mock_reserve.return_value = {"order_id": "test-id", "status": "RESERVED", "reserved_at": "2023-10-01T12:00:00Z"}
        
        payload = {
            "address_id": "addr-001", 
            "payment_method_id": "pm-001", 
            "comment": "Test"
        }
        response = client.post("/api/v1/orders", json=payload, headers=HEADERS)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PAID"
        assert data["total"] == 599800
        assert data["items"][0]["unit_price"] == 299900
        assert data["items"][0]["name"] == "Test Product - Black, L"

@patch("src.services.checkout_service.b2b_client.get_sku_details_batch")
@patch("src.services.checkout_service.cart_client.get_cart")
def test_partial_reserve_failure_returns_409(mock_get_cart, mock_get_sku):
    mock_get_cart.return_value = [
        {"sku_id": "sku-001", "quantity": 1},
        {"sku_id": "sku-002", "quantity": 1}
    ]
    mock_get_sku.return_value = {
        "sku-001": {"unit_price": 1000, "product_id": "p1", "product_title": "P1", "sku_name": "N1"},
        "sku-002": {"unit_price": 2000, "product_id": "p2", "product_title": "P2", "sku_name": "N2"}
    }
    
    with patch("src.services.checkout_service.b2b_client.reserve_inventory") as mock_reserve:
        mock_reserve.side_effect = ReserveFailedError([{"sku_id": "sku-002", "reason": "out_of_stock"}])
        
        payload = {"address_id": "addr-001", "payment_method_id": "pm-001"}
        headers = {**HEADERS, "Idempotency-Key": "checkout-002"}
        response = client.post("/api/v1/orders", json=payload, headers=headers)
        
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "RESERVE_FAILED"

@patch("src.services.checkout_service.b2b_client.get_sku_details_batch")
@patch("src.services.checkout_service.cart_client.get_cart")
def test_idempotency_returns_existing_order(mock_get_cart, mock_get_sku):
    mock_get_cart.return_value = [{"sku_id": "sku-003", "quantity": 1}]
    mock_get_sku.return_value = {
        "sku-003": {"unit_price": 150000, "product_id": "prod-003", "product_title": "Idem", "sku_name": "Red"}
    }
    
    with patch("src.services.checkout_service.b2b_client.reserve_inventory") as mock_reserve:
        mock_reserve.return_value = {"order_id": "test-id", "status": "RESERVED", "reserved_at": "2023-10-01T12:00:00Z"}
        
        payload = {"address_id": "addr-001", "payment_method_id": "pm-001"}
        headers = {**HEADERS, "Idempotency-Key": "checkout-idem"}
        
        resp1 = client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp1.status_code == 201
        order_id_1 = resp1.json()["id"]
        
        resp2 = client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp2.status_code == 201
        assert resp2.json()["id"] == order_id_1
        assert mock_reserve.call_count == 1

@patch("src.services.checkout_service.b2b_client.get_sku_details_batch")
@patch("src.services.checkout_service.cart_client.get_cart")
def test_b2b_unavailable_returns_503(mock_get_cart, mock_get_sku):
    mock_get_cart.return_value = [{"sku_id": "sku-001", "quantity": 1}]
    mock_get_sku.return_value = {
        "sku-001": {"unit_price": 1000, "product_id": "p1", "product_title": "P1", "sku_name": "N1"}
    }
    
    with patch("src.services.checkout_service.b2b_client.reserve_inventory") as mock_reserve:
        mock_reserve.side_effect = B2BUnavailableError("Service down")
        
        payload = {"address_id": "addr-001", "payment_method_id": "pm-001"}
        headers = {**HEADERS, "Idempotency-Key": "checkout-004"}
        response = client.post("/api/v1/orders", json=payload, headers=headers)
        
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"