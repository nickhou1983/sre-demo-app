import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import runtime_config
from app.services.checkout import (
    ConnectionPoolExhaustedError,
    ReleaseRegressionError,
    list_orders,
    process_checkout,
    verify_service_dependencies,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("sre-demo-app")

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(logger_name="sre-demo-app")
        logger.info("Azure Monitor OpenTelemetry initialized successfully.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to initialize Azure Monitor OpenTelemetry: %s", exc)

app = FastAPI(
    title="Contoso Order Service (Azure SRE Agent Demo)",
    version="1.1.0",
    description="Demo application for Azure SRE Agent Scenario 1: Bad Deployment / Config Change causing HTTP 503 Outage",
)

STATIC_DIR = Path(__file__).parent / "static"

METRICS: Dict[str, Any] = {
    "total_requests": 0,
    "http_2xx": 0,
    "http_5xx": 0,
    "last_latency_ms": 0.0,
}
RECENT_EVENTS: Deque[Dict[str, Any]] = deque(maxlen=40)


def record_event(level: str, endpoint: str, status_code: int, message: str, latency_ms: float) -> None:
    RECENT_EVENTS.appendleft(
        {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC",
            "level": level,
            "endpoint": endpoint,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 1),
            "message": message,
            "version": runtime_config.app_version,
            "fault_mode": runtime_config.fault_mode,
        }
    )


class CheckoutRequest(BaseModel):
    item: str = Field(default="Azure SRE Enterprise Node")
    amount: float = Field(default=299.0, gt=0)
    quantity: int = Field(default=1, ge=1)


class ChaosModeRequest(BaseModel):
    mode: str = Field(
        ...,
        description="One of: none, bad_config, bad_release, high_latency, reset_env",
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
@app.get("/api/health")
async def health_check(request: Request) -> JSONResponse:
    start = time.perf_counter()
    METRICS["total_requests"] += 1
    try:
        verify_service_dependencies(runtime_config)
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_2xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        record_event("INFO", request.url.path, 200, "Health check passed", latency_ms)
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "version": runtime_config.app_version,
                "fault_mode": runtime_config.fault_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except (ConnectionPoolExhaustedError, ReleaseRegressionError) as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_5xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        logger.exception("Health check failed with HTTP 503 on %s", request.url.path)
        record_event("ERROR", request.url.path, 503, str(exc), latency_ms)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error_type": exc.__class__.__name__,
                "detail": str(exc),
                "version": runtime_config.app_version,
                "fault_mode": runtime_config.fault_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@app.get("/api/orders")
async def get_orders(request: Request) -> JSONResponse:
    start = time.perf_counter()
    METRICS["total_requests"] += 1
    try:
        result = list_orders(runtime_config)
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_2xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        record_event("INFO", "/api/orders", 200, f"Fetched {result['count']} orders", latency_ms)
        return JSONResponse(status_code=200, content=result)
    except (ConnectionPoolExhaustedError, ReleaseRegressionError) as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_5xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        logger.exception("Order listing failed with HTTP 503 on /api/orders")
        record_event("ERROR", "/api/orders", 503, str(exc), latency_ms)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error_type": exc.__class__.__name__,
                "detail": str(exc),
                "version": runtime_config.app_version,
                "fault_mode": runtime_config.fault_mode,
            },
        )


@app.post("/api/checkout")
async def create_checkout(payload: CheckoutRequest) -> JSONResponse:
    start = time.perf_counter()
    METRICS["total_requests"] += 1
    try:
        result = process_checkout(
            runtime_config,
            item=payload.item,
            amount=payload.amount,
            quantity=payload.quantity,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_2xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        record_event(
            "INFO",
            "/api/checkout",
            200,
            f"Order {result['order_id']} confirmed (${result['total_amount']})",
            latency_ms,
        )
        return JSONResponse(status_code=200, content=result)
    except (ConnectionPoolExhaustedError, ReleaseRegressionError) as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        METRICS["http_5xx"] += 1
        METRICS["last_latency_ms"] = round(latency_ms, 1)
        logger.exception("Checkout transaction failed with HTTP 503 on /api/checkout")
        record_event("ERROR", "/api/checkout", 503, str(exc), latency_ms)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error_type": exc.__class__.__name__,
                "detail": str(exc),
                "version": runtime_config.app_version,
                "fault_mode": runtime_config.fault_mode,
            },
        )


@app.get("/api/status")
async def get_dashboard_status() -> Dict[str, Any]:
    """Out-of-band status endpoint for the UI dashboard (always returns HTTP 200)."""
    cfg = runtime_config.to_dict()
    is_healthy = not (cfg["is_config_broken"] or cfg["is_release_broken"])
    total = METRICS["total_requests"]
    error_rate = round((METRICS["http_5xx"] / total) * 100, 1) if total > 0 else 0.0
    return {
        "service_healthy": is_healthy,
        "config": cfg,
        "metrics": {
            **METRICS,
            "error_rate_pct": error_rate,
        },
        "recent_events": list(RECENT_EVENTS),
    }


@app.post("/api/chaos/mode")
async def set_chaos_mode(req: ChaosModeRequest) -> JSONResponse:
    mode = req.mode.strip().lower()
    if mode == "reset_env":
        runtime_config.reset_to_env()
        msg = "Reset runtime overrides to OS environment variables"
    else:
        try:
            runtime_config.apply_preset(mode)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        msg = f"Switched fault mode to '{mode}' (version={runtime_config.app_version})"

    logger.warning("CHAOS CONTROL: %s", msg)
    record_event("WARN", "/api/chaos/mode", 200, msg, 0.5)
    return JSONResponse(
        status_code=200,
        content={
            "message": msg,
            "config": runtime_config.to_dict(),
        },
    )


@app.post("/api/chaos/reset-metrics")
async def reset_metrics() -> Dict[str, Any]:
    METRICS["total_requests"] = 0
    METRICS["http_2xx"] = 0
    METRICS["http_5xx"] = 0
    METRICS["last_latency_ms"] = 0.0
    RECENT_EVENTS.clear()
    return {"status": "reset"}
