
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_event_type():
    payload = {
        "event_id": "pytest-invalid-001",
        "event_type": "invalid_event",
        "transaction_id": "pytest-txn-001",
        "merchant_id": "pytest-merchant-001",
        "merchant_name": "Pytest Merchant",
        "amount": 1000,
        "currency": "INR",
        "timestamp": "2026-09-25T10:00:00Z",
    }

    response = client.post("/events", json=payload)

    assert response.status_code == 422


def test_transaction_not_found():
    response = client.get(
        "/transactions/non-existent-transaction-123"
    )

    assert response.status_code == 404


def test_get_transactions():
    response = client.get(
        "/transactions",
        params={
            "page": 1,
            "page_size": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 5
    assert data["total"] == 3800
    assert len(data["transactions"]) == 5

