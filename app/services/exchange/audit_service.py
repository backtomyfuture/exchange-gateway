"""
审计日志服务
记录和查询管理操作日志
"""

from datetime import datetime, timedelta

from app.log import logger
from app.models.exchange import ExchangeAuditLog


class AuditService:
    """
    审计日志服务
    提供日志记录和查询功能
    """

    async def log(
        self,
        operator_id: int,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        resource_name: str | None = None,
        details: dict | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
        operator_name: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> ExchangeAuditLog:
        """
        记录审计日志

        Args:
            operator_id: 操作者ID
            action: 操作类型（create_account, delete_api_key 等）
            resource_type: 资源类型（account, api_key, template）
            resource_id: 资源ID
            resource_name: 资源名称（如邮箱地址、密钥名称）
            details: 操作详情（如变更前后对比）
            request_ip: 请求IP
            user_agent: User-Agent
            operator_name: 操作者用户名
            status: 状态（success, failed）
            error_message: 错误信息

        Returns:
            ExchangeAuditLog: 创建的日志记录
        """
        try:
            log_entry = await ExchangeAuditLog.create(
                operator_id=operator_id,
                operator_name=operator_name,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                details=details,
                request_ip=request_ip,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
            )

            logger.info(
                f"审计日志: {action} {resource_type} (id={resource_id}, name={resource_name}) by user {operator_id}"
            )
            return log_entry

        except Exception as e:
            # 审计日志失败不应影响主业务
            logger.error(f"审计日志记录失败: {e}")
            raise

    async def log_success(
        self,
        operator_id: int,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        resource_name: str | None = None,
        details: dict | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
        operator_name: str | None = None,
    ) -> ExchangeAuditLog:
        """记录成功的操作"""
        return await self.log(
            operator_id=operator_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            request_ip=request_ip,
            user_agent=user_agent,
            operator_name=operator_name,
            status="success",
        )

    async def log_failure(
        self,
        operator_id: int,
        action: str,
        resource_type: str,
        error_message: str,
        resource_id: int | None = None,
        resource_name: str | None = None,
        details: dict | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
        operator_name: str | None = None,
    ) -> ExchangeAuditLog:
        """记录失败的操作"""
        return await self.log(
            operator_id=operator_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            request_ip=request_ip,
            user_agent=user_agent,
            operator_name=operator_name,
            status="failed",
            error_message=error_message,
        )

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        operator_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """
        查询审计日志列表

        Returns:
            dict: {"total": int, "items": list}
        """
        query = ExchangeAuditLog.all()

        # 过滤条件
        if operator_id:
            query = query.filter(operator_id=operator_id)
        if action:
            query = query.filter(action=action)
        if resource_type:
            query = query.filter(resource_type=resource_type)
        if resource_id:
            query = query.filter(resource_id=resource_id)
        if status:
            query = query.filter(status=status)
        if date_from:
            query = query.filter(created_at__gte=date_from)
        if date_to:
            query = query.filter(created_at__lte=date_to)

        # 总数
        total = await query.count()

        # 分页
        offset = (page - 1) * page_size
        items = await query.order_by("-created_at").offset(offset).limit(page_size)

        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "operator_id": item.operator_id,
                    "operator_name": item.operator_name,
                    "action": item.action,
                    "resource_type": item.resource_type,
                    "resource_id": item.resource_id,
                    "resource_name": item.resource_name,
                    "details": item.details,
                    "request_ip": item.request_ip,
                    "status": item.status,
                    "error_message": item.error_message,
                    "created_at": item.created_at,
                }
                for item in items
            ],
        }

    async def get_recent_activity(
        self,
        operator_id: int | None = None,
        hours: int = 24,
        limit: int = 10,
    ) -> list:
        """
        获取最近活动

        Args:
            operator_id: 可选，只获取指定用户的活动
            hours: 时间范围（小时）
            limit: 返回数量

        Returns:
            list: 最近活动列表
        """
        query = ExchangeAuditLog.filter(created_at__gte=datetime.now() - timedelta(hours=hours))

        if operator_id:
            query = query.filter(operator_id=operator_id)

        items = await query.order_by("-created_at").limit(limit)

        return [
            {
                "id": item.id,
                "action": item.action,
                "resource_type": item.resource_type,
                "resource_name": item.resource_name,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in items
        ]


# 全局服务实例
_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """获取审计服务实例"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
