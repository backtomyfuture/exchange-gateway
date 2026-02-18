"""Prometheus metrics for exchange-gateway.

HTTP metrics: handled automatically by prometheus_fastapi_instrumentator.
Exchange-specific metrics: defined here, incremented manually.
"""
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

email_sent_total = Counter(
    "exchange_email_sent_total",
    "Total email send outcomes",
    ["account_id", "status"],  # status: success | failed
)

email_duration_seconds = Histogram(
    "exchange_email_duration_seconds",
    "Email send round-trip duration in seconds",
    ["account_id"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

connection_pool_active = Gauge(
    "exchange_connection_pool_active",
    "Active Exchange connections per account",
    ["account_id"],
)

circuit_breaker_state = Gauge(
    "exchange_circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=open, 2=half_open",
    ["account_id"],
)

webhook_delivery_total = Counter(
    "exchange_webhook_delivery_total",
    "Total webhook delivery outcomes",
    ["status"],  # delivered | dead
)


def setup_instrumentator(app) -> None:
    """Register Prometheus instrumentation. Call once after creating the FastAPI app."""
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")
