from fastapi.testclient import TestClient

from app.config import runtime_config
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    runtime_config.apply_preset("none")
    client.post("/api/chaos/reset-metrics")


def test_healthy_endpoints() -> None:
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_orders = client.get("/api/orders")
    assert res_orders.status_code == 200
    assert res_orders.json()["count"] >= 3

    res_checkout = client.post(
        "/api/checkout",
        json={"item": "Azure SRE Agent License", "amount": 199.0, "quantity": 2},
    )
    assert res_checkout.status_code == 200
    body = res_checkout.json()
    assert body["status"] == "confirmed"
    assert body["total_amount"] == 398.0


def test_bad_config_triggers_503() -> None:
    res_mode = client.post("/api/chaos/mode", json={"mode": "bad_config"})
    assert res_mode.status_code == 200

    res_health = client.get("/health")
    assert res_health.status_code == 503
    assert res_health.json()["error_type"] == "ConnectionPoolExhaustedError"

    res_checkout = client.post(
        "/api/checkout",
        json={"item": "Test Item", "amount": 50.0, "quantity": 1},
    )
    assert res_checkout.status_code == 503
    assert "DB_MAX_CONNECTIONS=0" in res_checkout.json()["detail"]

    status_data = client.get("/api/status").json()
    assert status_data["service_healthy"] is False
    assert status_data["metrics"]["http_5xx"] == 2


def test_bad_release_triggers_503_and_recovery() -> None:
    client.post("/api/chaos/mode", json={"mode": "bad_release"})

    res_orders = client.get("/api/orders")
    assert res_orders.status_code == 503
    data = res_orders.json()
    assert data["error_type"] == "ReleaseRegressionError"
    assert data["version"] == "1.2.0-buggy"
    assert "discount_tier_v2_multiplier" in data["detail"]

    # Recover back to healthy
    client.post("/api/chaos/mode", json={"mode": "none"})
    res_recovered = client.get("/health")
    assert res_recovered.status_code == 200
    assert res_recovered.json()["version"] == "1.1.0-stable"
