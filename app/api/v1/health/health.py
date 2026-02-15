"""
健康检查端点
用于容器编排和负载均衡器的健康检查
"""
from fastapi import APIRouter
from tortoise import Tortoise

from app.schemas.base import Success
from app.settings import settings

router = APIRouter()


@router.get("", summary="健康检查")
async def health_check():
    """
    基础健康检查端点
    返回应用运行状态
    """
    return Success(
        data={
            "status": "healthy",
            "version": settings.VERSION,
        }
    )


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    """
    就绪检查端点
    检查应用是否准备好接收流量（包括数据库连接）
    """
    checks = {
        "database": False,
    }
    
    # 检查数据库连接
    try:
        conn = Tortoise.get_connection("mysql")
        await conn.execute_query("SELECT 1")
        checks["database"] = True
    except Exception:
        pass
    
    all_healthy = all(checks.values())
    
    return Success(
        data={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
        }
    )


@router.get("/live", summary="存活检查")
async def liveness_check():
    """
    存活检查端点
    仅检查应用进程是否存活
    """
    return Success(
        data={
            "status": "alive",
        }
    )
