import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import RuntimeConfig


class ConnectionPoolExhaustedError(RuntimeError):
    """Raised when DB_MAX_CONNECTIONS is misconfigured (<= 0) or payment gateway URL is invalid."""


class ReleaseRegressionError(RuntimeError):
    """Raised when a bad code deployment introduces an unhandled regression in checkout pipeline."""


SAMPLE_ORDERS: List[Dict[str, Any]] = [
    {"order_id": "ORD-9001", "item": "Azure AI GPU Node Reservation", "amount": 1299.00, "status": "completed"},
    {"order_id": "ORD-9002", "item": "Enterprise SRE Monitoring Pack", "amount": 499.00, "status": "processing"},
    {"order_id": "ORD-9003", "item": "Contoso Cloud Storage 10TB", "amount": 199.00, "status": "completed"},
]


def verify_service_dependencies(cfg: RuntimeConfig) -> None:
    """Validate downstream dependencies and configuration settings before serving requests."""
    if cfg.fault_mode == "high_latency":
        time.sleep(2.2)

    if cfg.is_config_broken:
        raise ConnectionPoolExhaustedError(
            f"HTTP 503 Service Unavailable: Downstream connection pool failed to initialize. "
            f"Current configuration: DB_MAX_CONNECTIONS={cfg.db_max_connections} (must be > 0), "
            f"PAYMENT_GATEWAY_URL='{cfg.payment_gateway_url}', FAULT_MODE='{cfg.fault_mode}'. "
            f"Remediation: Restore App Service settings DB_MAX_CONNECTIONS=50 and FAULT_MODE=none."
        )

    if cfg.is_release_broken:
        # Simulate a code regression introduced in release v1.2.0-buggy
        payload_context = {"order_schema_version": "v2", "currency": "USD"}
        try:
            _ = payload_context["discount_tier_v2_multiplier"]
        except KeyError as exc:
            raise ReleaseRegressionError(
                f"HTTP 503 Service Unavailable: Unhandled KeyError {exc} in app/services/checkout.py "
                f"introduced in deployment APP_VERSION='{cfg.app_version}' (FAULT_MODE='{cfg.fault_mode}'). "
                f"Remediation: Roll back deployment to '1.1.0-stable' or set FAULT_MODE=none."
            ) from exc


def list_orders(cfg: RuntimeConfig) -> Dict[str, Any]:
    verify_service_dependencies(cfg)
    return {
        "version": cfg.app_version,
        "count": len(SAMPLE_ORDERS),
        "orders": SAMPLE_ORDERS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def process_checkout(cfg: RuntimeConfig, item: str, amount: float, quantity: int = 1) -> Dict[str, Any]:
    verify_service_dependencies(cfg)
    order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    return {
        "order_id": order_id,
        "item": item,
        "quantity": quantity,
        "total_amount": round(amount * quantity, 2),
        "payment_gateway": cfg.payment_gateway_url,
        "version": cfg.app_version,
        "status": "confirmed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
