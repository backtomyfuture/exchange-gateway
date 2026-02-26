"""
Exchange 服务健康检查 API
"""

from fastapi import APIRouter

from app.log import logger
from app.schemas.base import Success
from app.services.exchange import get_connection_pool

router = APIRouter()


@router.get("/health", summary="服务健康检查")
async def health_check():
    """
    检查 Exchange 邮件服务状态

    返回:
    - 服务状态
    - 数据库连接状态
    - Exchange 连接池状态
    """
    try:
        # 检查连接池状态
        pool = get_connection_pool()
        pool_status = {
            "active_accounts": len(pool._pools),
            "total_connections": sum(len(p) for p in pool._pools.values()),
        }

        return Success(
            data={
                "status": "healthy",
                "services": {
                    "exchange_pool": pool_status,
                },
            }
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return Success(
            data={
                "status": "degraded",
                "error": str(e),
            }
        )


@router.get("/health/detailed", summary="详细健康检查")
async def detailed_health_check():
    """
    详细的服务健康检查

    包含:
    - 连接池详情
    - 各账户连接状态
    """
    try:
        from datetime import datetime, timedelta

        from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeMailLog

        # 连接池状态
        pool = get_connection_pool()

        # 统计数据
        total_accounts = await ExchangeAccount.filter(is_active=True).count()
        total_api_keys = await ExchangeApiKey.filter(is_active=True).count()

        # 最近24小时邮件统计
        cutoff = datetime.now() - timedelta(hours=24)
        recent_logs = await ExchangeMailLog.filter(created_at__gte=cutoff).count()
        recent_success = await ExchangeMailLog.filter(created_at__gte=cutoff, status="success").count()
        recent_pending = await ExchangeMailLog.filter(created_at__gte=cutoff, status="pending").count()

        return Success(
            data={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "connection_pool": {
                    "active_accounts": len(pool._pools),
                    "total_connections": sum(len(p) for p in pool._pools.values()),
                },
                "statistics": {
                    "active_accounts": total_accounts,
                    "active_api_keys": total_api_keys,
                    "emails_last_24h": {
                        "total": recent_logs,
                        "success": recent_success,
                        "pending": recent_pending,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        return Success(
            data={
                "status": "degraded",
                "error": str(e),
            }
        )


@router.post("/warmup", summary="预热连接池")
async def warmup_connection_pool(
    account_id: int | None = None,
    min_connections: int = 2,
):
    """
    预热 Exchange 连接池

    Args:
        account_id: 指定账户ID（不传则预热所有活跃账户）
        min_connections: 每个账户的最小连接数（默认2）

    Returns:
        预热结果统计
    """
    try:
        pool = get_connection_pool()

        if account_id:
            # 预热指定账户
            result = await pool.warmup_connections(account_id, min_connections)
            return Success(data={"mode": "single", "account_id": account_id, **result})
        else:
            # 预热所有账户
            results = await pool.warmup_all_accounts(min_connections)
            return Success(data={"mode": "all", **results})

    except Exception as e:
        logger.error(f"连接预热失败: {e}")
        return Success(
            data={
                "success": False,
                "message": f"连接预热失败: {str(e)}",
            }
        )


@router.get("/pool/stats", summary="连接池统计")
async def get_pool_stats():
    """
    获取连接池详细统计信息

    Returns:
        连接池统计，包括总连接数、各账户连接数、预热状态
    """
    try:
        pool = get_connection_pool()
        stats = pool.get_stats()

        return Success(data=stats)

    except Exception as e:
        logger.error(f"获取连接池统计失败: {e}")
        return Success(
            data={
                "error": str(e),
            }
        )
