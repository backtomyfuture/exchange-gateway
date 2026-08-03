from datetime import datetime

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from app.models.admin import AuditLog
from app.schemas import SuccessExtra

router = APIRouter()


@router.get("/list", summary="查看操作日志")
async def get_audit_log_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="操作人名称"),
    module: str = Query("", description="功能模块"),
    method: str = Query("", description="请求方法"),
    summary: str = Query("", description="接口描述"),
    path: str = Query("", description="请求路径"),
    status: int = Query(None, description="状态码"),
    start_time: datetime = Query("", description="开始时间"),
    end_time: datetime = Query("", description="结束时间"),
):
    q = Q()
    if username:
        q &= Q(username__icontains=username)
    if module:
        q &= Q(module__icontains=module)
    if method:
        q &= Q(method__icontains=method)
    if summary:
        q &= Q(summary__icontains=summary)
    if path:
        q &= Q(path__icontains=path)
    if status:
        q &= Q(status=status)
    if start_time and end_time:
        q &= Q(created_at__range=[start_time, end_time])
    elif start_time:
        q &= Q(created_at__gte=start_time)
    elif end_time:
        q &= Q(created_at__lte=end_time)

    # 先排序再分页，配合 created_at 索引避免大表在分页后进行全量内存排序。
    queryset = AuditLog.filter(q)
    total = await queryset.count()
    audit_log_objs = await queryset.order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    data = [await audit_log.to_dict() for audit_log in audit_log_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
