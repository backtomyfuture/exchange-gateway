"""
账户服务
提供邮箱账户的管理功能
"""
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

from app.log import logger
from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeMailLog, ExchangeAuditLog

from app.schemas.exchange import AccountCreate, AccountUpdate, ApiKeyCreate
from app.settings import settings
from app.utils.crypto import get_crypto, generate_api_key, hash_api_key

from .connection_pool import get_connection_pool, get_exchange_connection
from .audit_service import get_audit_service


class AccountService:
    """
    账户服务
    管理邮箱账户和 API 密钥
    """
    
    def __init__(self):
        self._crypto = None
    
    @property
    def crypto(self):
        if self._crypto is None:
            self._crypto = get_crypto()
        return self._crypto
    
    # =========================================================================
    # 邮箱账户管理
    # =========================================================================
    
    async def create_account(self, data: AccountCreate, owner_id: int) -> dict:
        """
        创建邮箱账户
        """
        try:
            # 检查是否已存在
            existing = await ExchangeAccount.filter(email=data.email).first()
            if existing:
                return {
                    "success": False,
                    "message": f"邮箱账户已存在: {data.email}",
                }
            
            # 加密密码
            encrypted_password = self.crypto.encrypt(data.password)
            
            # 创建账户
            account = await ExchangeAccount.create(
                email=data.email,
                username=data.username,
                encrypted_password=encrypted_password,
                display_name=data.display_name,
                server=data.server,
                domain=data.domain,
                remark=data.remark,
                owner_id=owner_id,
                is_active=True,
                is_verified=False,
            )
            
            logger.info(f"邮箱账户创建成功: {data.email}")
            
            # 记录审计日志
            audit = get_audit_service()
            await audit.log_success(
                operator_id=owner_id,
                action="create_account",
                resource_type="account",
                resource_id=account.id,
                resource_name=data.email,
                details={"display_name": data.display_name, "server": data.server},
            )
            
            return {
                "success": True,
                "message": "账户创建成功",
                "data": await account.to_dict(exclude_fields=["encrypted_password"]),
            }
            
        except Exception as e:
            logger.error(f"创建邮箱账户失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {e}",
            }
    
    async def update_account(self, data: AccountUpdate, owner_id: int) -> dict:
        """
        更新邮箱账户
        """
        try:
            account = await ExchangeAccount.filter(id=data.id, owner_id=owner_id).first()
            if not account:
                return {
                    "success": False,
                    "message": "账户不存在或无权限",
                }
            
            # 更新字段
            if data.display_name is not None:
                account.display_name = data.display_name
            if data.server is not None:
                account.server = data.server
            if data.domain is not None:
                account.domain = data.domain
            if data.is_active is not None:
                account.is_active = data.is_active
            if data.remark is not None:
                account.remark = data.remark
            
            # 如果更新密码
            if data.password:
                account.encrypted_password = self.crypto.encrypt(data.password)
                account.is_verified = False  # 需要重新验证
                # 关闭现有连接
                pool = get_connection_pool()
                await pool.close_account_connections(account.id)
            
            await account.save()
            
            logger.info(f"邮箱账户更新成功: {account.email}")
            
            # 记录审计日志
            audit = get_audit_service()
            await audit.log_success(
                operator_id=owner_id,
                action="update_account",
                resource_type="account",
                resource_id=account.id,
                resource_name=account.email,
                details={"password_changed": bool(data.password)},
            )
            
            return {
                "success": True,
                "message": "更新成功",
                "data": await account.to_dict(exclude_fields=["encrypted_password"]),
            }
            
        except Exception as e:
            logger.error(f"更新邮箱账户失败: {e}")
            return {
                "success": False,
                "message": f"更新失败: {e}",
            }
    
    async def delete_account(self, account_id: int, owner_id: int) -> dict:
        """
        删除邮箱账户
        """
        try:
            account = await ExchangeAccount.filter(id=account_id, owner_id=owner_id).first()
            if not account:
                return {
                    "success": False,
                    "message": "账户不存在或无权限",
                }
            
            email = account.email
            
            # 关闭连接
            pool = get_connection_pool()
            await pool.close_account_connections(account_id)
            
            # 删除账户
            await account.delete()
            
            logger.info(f"邮箱账户删除成功: {email}")
            
            # 记录审计日志
            audit = get_audit_service()
            await audit.log_success(
                operator_id=owner_id,
                action="delete_account",
                resource_type="account",
                resource_id=account_id,
                resource_name=email,
            )
            
            return {
                "success": True,
                "message": "删除成功",
            }
            
        except Exception as e:
            logger.error(f"删除邮箱账户失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {e}",
            }
    
    async def test_account(self, account_id: int, owner_id: int) -> dict:
        """
        测试邮箱账户连接
        """
        try:
            account = await ExchangeAccount.filter(id=account_id, owner_id=owner_id).first()
            if not account:
                return {
                    "success": False,
                    "message": "账户不存在或无权限",
                }
            
            # 尝试获取连接
            async with get_exchange_connection(account_id) as conn:
                # 验证连接 (Blocking call wrapped in thread pool)
                import asyncio
                loop = asyncio.get_running_loop()
                inbox_count = await loop.run_in_executor(
                    None,
                    lambda: conn.account.inbox.total_count
                )
                
                # 更新验证状态
                account.is_verified = True
                account.last_verified_at = datetime.now()
                await account.save()
                
                return {
                    "success": True,
                    "message": f"连接成功！收件箱邮件数: {inbox_count}",
                }
                
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            
            # 更新验证状态
            if account:
                account.is_verified = False
                await account.save()
            
            return {
                "success": False,
                "message": f"连接失败: {e}",
            }
    
    async def list_accounts(self, owner_id: int, page: int = 1, page_size: int = 20) -> dict:
        """
        获取账户列表
        """
        try:
            total = await ExchangeAccount.filter(owner_id=owner_id).count()
            accounts = await ExchangeAccount.filter(owner_id=owner_id).offset(
                (page - 1) * page_size
            ).limit(page_size)
            
            items = [
                await acc.to_dict(exclude_fields=["encrypted_password"])
                for acc in accounts
            ]
            
            return {
                "success": True,
                "total": total,
                "items": items,
            }
            
        except Exception as e:
            logger.error(f"获取账户列表失败: {e}")
            return {
                "success": False,
                "total": 0,
                "items": [],
                "message": str(e),
            }
    
    # =========================================================================
    # API 密钥管理
    # =========================================================================
    
    async def create_api_key(self, data: ApiKeyCreate, owner_id: int) -> dict:
        """
        创建 API 密钥
        """
        try:
            # 生成密钥
            raw_key = generate_api_key()
            key_hash = hash_api_key(raw_key)
            key_prefix = raw_key[:8]
            
            # 计算过期时间
            expires_days = data.expires_days or settings.EXCHANGE_API_KEY_EXPIRE_DAYS
            expires_at = datetime.now() + timedelta(days=expires_days) if expires_days else None
            
            # 创建记录
            api_key = await ExchangeApiKey.create(
                name=data.name,
                key_prefix=key_prefix,
                key_hash=key_hash,
                permissions=data.permissions,
                allowed_accounts=data.allowed_accounts,
                ip_whitelist=data.ip_whitelist,
                rate_limit=data.rate_limit,
                expires_at=expires_at,
                owner_id=owner_id,
                remark=data.remark,
            )
            
            logger.info(f"API 密钥创建成功: {data.name} ({key_prefix}...)")
            
            # 记录审计日志
            audit = get_audit_service()
            await audit.log_success(
                operator_id=owner_id,
                action="create_api_key",
                resource_type="api_key",
                resource_id=api_key.id,
                resource_name=data.name,
                details={"permissions": data.permissions, "rate_limit": data.rate_limit},
            )
            
            return {
                "success": True,
                "message": "API 密钥创建成功（请妥善保存，密钥仅显示一次）",
                "data": {
                    "id": api_key.id,
                    "name": api_key.name,
                    "api_key": raw_key,  # 仅此一次显示完整密钥
                    "key_prefix": key_prefix,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                },
            }
            
        except Exception as e:
            logger.error(f"创建 API 密钥失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {e}",
            }
    
    async def revoke_api_key(self, key_id: int, owner_id: int) -> dict:
        """
        撤销 API 密钥
        """
        try:
            api_key = await ExchangeApiKey.filter(id=key_id, owner_id=owner_id).first()
            if not api_key:
                return {
                    "success": False,
                    "message": "密钥不存在或无权限",
                }
            
            api_key.is_active = False
            await api_key.save()
            
            logger.info(f"API 密钥已撤销: {api_key.name}")
            
            # 记录审计日志
            audit = get_audit_service()
            await audit.log_success(
                operator_id=owner_id,
                action="revoke_api_key",
                resource_type="api_key",
                resource_id=key_id,
                resource_name=api_key.name,
            )
            
            return {
                "success": True,
                "message": "密钥已撤销",
            }
            
        except Exception as e:
            logger.error(f"撤销 API 密钥失败: {e}")
            return {
                "success": False,
                "message": f"撤销失败: {e}",
            }
    
    async def delete_api_key(self, key_id: int, owner_id: int) -> dict:
        """
        删除 API 密钥
        """
        try:
            api_key = await ExchangeApiKey.filter(id=key_id, owner_id=owner_id).first()
            if not api_key:
                return {
                    "success": False,
                    "message": "密钥不存在或无权限",
                }
            
            name = api_key.name
            await api_key.delete()
            
            logger.info(f"API 密钥已删除: {name}")
            
            return {
                "success": True,
                "message": "密钥已删除",
            }
            
        except Exception as e:
            logger.error(f"删除 API 密钥失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {e}",
            }
    
    async def list_api_keys(self, owner_id: int, page: int = 1, page_size: int = 20) -> dict:
        """
        获取 API 密钥列表
        """
        try:
            total = await ExchangeApiKey.filter(owner_id=owner_id).count()
            keys = await ExchangeApiKey.filter(owner_id=owner_id).offset(
                (page - 1) * page_size
            ).limit(page_size)
            
            items = [
                await key.to_dict(exclude_fields=["key_hash"])
                for key in keys
            ]
            
            return {
                "success": True,
                "total": total,
                "items": items,
            }
            
        except Exception as e:
            logger.error(f"获取 API 密钥列表失败: {e}")
            return {
                "success": False,
                "total": 0,
                "items": [],
                "message": str(e),
            }
    
    # =========================================================================
    # 使用统计
    # =========================================================================
    
    async def get_usage_stats(
        self,
        owner_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        """
        获取使用统计
        """
        try:
            # 默认最近30天
            if not date_from:
                date_from = datetime.now().astimezone() - timedelta(days=30)
            if not date_to:
                date_to = datetime.now().astimezone()
            
            # 确保带时区
            if date_from and not date_from.tzinfo:
                date_from = date_from.astimezone()
            if date_to and not date_to.tzinfo:
                date_to = date_to.astimezone()
            
            # 获取用户的账户ID列表
            accounts = await ExchangeAccount.filter(owner_id=owner_id).values_list("id", flat=True)
            
            # 查询日志
            logs = await ExchangeMailLog.filter(
                account_id__in=accounts,
                created_at__gte=date_from,
                created_at__lte=date_to,
            )
            
            # 统计
            total_count = len(logs)
            success_count = len([l for l in logs if l.status == "success"])
            failed_count = len([l for l in logs if l.status == "failed"])
            
            # 今日数据
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_logs = [l for l in logs if l.created_at.strftime("%Y-%m-%d") == today_str]
            today_count = len(today_logs)

            # 活跃数据
            active_accounts = await ExchangeAccount.filter(owner_id=owner_id, is_active=True).count()
            active_api_keys = await ExchangeApiKey.filter(owner_id=owner_id, is_active=True).count()

            by_action = {}
            daily_stats_map = {}
            
            for log in logs:
                # Action count
                action = log.action
                by_action[action] = by_action.get(action, 0) + 1
                
                # Daily stats
                day_str = log.created_at.strftime("%Y-%m-%d")
                if day_str not in daily_stats_map:
                    daily_stats_map[day_str] = {"date": day_str, "total": 0, "success": 0, "failed": 0}
                
                daily_stats_map[day_str]["total"] += 1
                if log.status == "success":
                    daily_stats_map[day_str]["success"] += 1
                elif log.status == "failed":
                    daily_stats_map[day_str]["failed"] += 1

            # 填充日期范围内的每一天，确保图表连续
            daily_stats = []
            current_date = date_from
            while current_date <= date_to:
                day_str = current_date.strftime("%Y-%m-%d")
                if day_str in daily_stats_map:
                    daily_stats.append(daily_stats_map[day_str])
                else:
                    daily_stats.append({"date": day_str, "total": 0, "success": 0, "failed": 0})
                current_date += timedelta(days=1)
            
            # Sort by date descending
            daily_stats.sort(key=lambda x: x["date"], reverse=True)

            return {
                "success": True,
                "stats": {
                    "total_count": total_count,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "success_rate": round(success_count / total_count * 100, 2) if total_count else 0,
                    "today_count": today_count,
                    "active_accounts": active_accounts,
                    "active_api_keys": active_api_keys,
                    "by_action": by_action,
                    "daily_stats": daily_stats,
                },
            }
            
        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return {
                "success": False,
                "stats": {},
                "message": str(e),
            }
    
    async def get_dashboard_data(self, owner_id: int) -> dict:
        """
        获取仪表盘数据
        """
        try:
            now = datetime.now().astimezone()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 1. 今日统计
            stats_result = await self.get_usage_stats(
                owner_id=owner_id,
                date_from=today_start,
                date_to=now,
            )
            today_stats = stats_result.get("stats", {})
            
            # 2. 最近日志 (取前5条)
            logs_result = await self.list_mail_logs(
                owner_id=owner_id,
                page=1,
                page_size=5,
            )
            recent_logs = logs_result.get("items", [])
            
            # 3. 账户状态
            active_accounts = await ExchangeAccount.filter(
                owner_id=owner_id, 
                is_active=True
            ).count()
            
            total_accounts = await ExchangeAccount.filter(owner_id=owner_id).count()
            
            return {
                "success": True,
                "data": {
                    "today_stats": today_stats,
                    "recent_logs": recent_logs,
                    "account_stats": {
                        "active": active_accounts,
                        "total": total_accounts,
                    }
                }
            }
        except Exception as e:
            logger.error(f"获取仪表盘数据失败: {e}")
            return {
                "success": False,
                "message": str(e),
            }



    async def list_mail_logs(
        self,
        owner_id: int,
        page: int = 1,
        page_size: int = 20,
        action: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """
        获取邮件日志列表
        """
        try:
            # 获取用户的账户ID列表
            accounts = await ExchangeAccount.filter(owner_id=owner_id).values_list("id", flat=True)
            
            # 构建查询
            query = ExchangeMailLog.filter(account_id__in=accounts)
            if action:
                query = query.filter(action=action)
            if status:
                query = query.filter(status=status)
            
            total = await query.count()
            logs = await query.order_by("-created_at").offset(
                (page - 1) * page_size
            ).limit(page_size)
            
            # 获取账户信息
            account_map = {
                acc.id: acc.email
                for acc in await ExchangeAccount.filter(id__in=accounts)
            }
            
            # 获取 API Key 信息
            key_ids = [log.api_key_id for log in logs if log.api_key_id]
            key_map = {}
            if key_ids:
                keys = await ExchangeApiKey.filter(id__in=key_ids)
                key_map = {key.id: key.name for key in keys}
            
            items = []
            for log in logs:
                log_dict = await log.to_dict()
                log_dict["account_email"] = account_map.get(log.account_id)
                log_dict["api_key_name"] = key_map.get(log.api_key_id) if log.api_key_id else None
                items.append(log_dict)
            
            return {
                "success": True,
                "total": total,
                "items": items,
            }
            
        except Exception as e:
            logger.error(f"获取邮件日志失败: {e}")
            return {
                "success": False,
                "total": 0,
                "items": [],
                "message": str(e),
            }


# 全局服务实例
@lru_cache(maxsize=1)
def get_account_service() -> AccountService:
    """获取账户服务实例"""
    return AccountService()
