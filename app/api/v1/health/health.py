"""Enhanced health check: 200 (healthy) / 207 (degraded) / 503 (unhealthy)."""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from tortoise import Tortoise

from app.settings import settings

router = APIRouter()


async def _check_database() -> dict:
    try:
        start = time.monotonic()
        conn = Tortoise.get_connection("default")
        await conn.execute_query("SELECT 1")
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def _check_redis() -> dict:
    try:
        from app.core.arq_pool import get_arq_pool

        start = time.monotonic()
        await get_arq_pool().ping()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def _check_exchange_accounts() -> dict:
    try:
        from app.services.exchange.circuit_breaker import CircuitState
        from app.services.exchange.connection_pool import get_connection_pool

        breakers = get_connection_pool()._circuit_breakers
        open_ids = [aid for aid, cb in breakers.items() if cb.state == CircuitState.OPEN]
        return {
            "status": "degraded" if open_ids else "ok",
            "total_monitored": len(breakers),
            "circuit_open": len(open_ids),
            "open_account_ids": open_ids,
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


@router.get("", summary="详细健康检查")
async def health_check():
    """Returns 200 (healthy), 207 (degraded), or 503 (unhealthy)."""
    db = await _check_database()
    redis = await _check_redis()
    exchange = await _check_exchange_accounts()

    critical_ok = db["status"] == "ok" and redis["status"] == "ok"
    fully_healthy = critical_ok and exchange.get("circuit_open", 0) == 0

    if not critical_ok:
        overall, http_status = "unhealthy", 503
    elif not fully_healthy:
        overall, http_status = "degraded", 207
    else:
        overall, http_status = "healthy", 200

    return JSONResponse(
        status_code=http_status,
        content={
            "code": 200,
            "msg": "success",
            "data": {
                "status": overall,
                "version": settings.VERSION,
                "checks": {"database": db, "redis": redis, "exchange_accounts": exchange},
            },
        },
    )


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    db = await _check_database()
    code = 200 if db["status"] == "ok" else 503
    return JSONResponse(
        status_code=code,
        content={"code": 200, "msg": "success", "data": {"database": db}},
    )


@router.get("/live", summary="存活检查")
async def liveness_check():
    return {"code": 200, "msg": "success", "data": {"status": "alive"}}
