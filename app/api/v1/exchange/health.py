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
        
        return Success(data={
            "status": "healthy",
            "services": {
                "exchange_pool": pool_status,
            }
        })
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return Success(data={
            "status": "degraded",
            "error": str(e),
        })


@router.get("/health/detailed", summary="详细健康检查")
async def detailed_health_check():
    """
    详细的服务健康检查
    
    包含:
    - 连接池详情
    - 各账户连接状态
    """
    try:
        from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeMailLog
        from datetime import datetime, timedelta
        
        # 连接池状态
        pool = get_connection_pool()
        
        # 统计数据
        total_accounts = await ExchangeAccount.filter(is_active=True).count()
        total_api_keys = await ExchangeApiKey.filter(is_active=True).count()
        
        # 最近24小时邮件统计
        cutoff = datetime.now() - timedelta(hours=24)
        recent_logs = await ExchangeMailLog.filter(created_at__gte=cutoff).count()
        recent_success = await ExchangeMailLog.filter(
            created_at__gte=cutoff,
            status="success"
        ).count()
        recent_pending = await ExchangeMailLog.filter(
            created_at__gte=cutoff,
            status="pending"
        ).count()
        
        return Success(data={
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
                }
            }
        })
        
    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        return Success(data={
            "status": "degraded",
            "error": str(e),
        })
