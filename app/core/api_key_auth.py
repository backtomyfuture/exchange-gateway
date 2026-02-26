"""
API 密钥认证中间件
用于第三方系统调用邮件接口的认证
"""

from datetime import UTC, datetime

from fastapi import Header, HTTPException, Request

from app.core.redis_rate_limiter import get_rate_limiter
from app.log import logger
from app.models.exchange import ExchangeApiKey
from app.utils.crypto import hash_api_key


class ApiKeyAuth:
    """
    API 密钥认证依赖

    使用方式:
        @router.post("/send")
        async def send_email(
            request: EmailSendRequest,
            api_key: ExchangeApiKey = Depends(ApiKeyAuth())
        ):
            ...
    """

    def __init__(self, required_permissions: list[str] | None = None, auto_error: bool = True):
        """
        初始化认证器

        Args:
            required_permissions: 需要的权限列表，如 ["send", "receive"]
            auto_error: 是否自动抛出异常，默认为 True。如果为 False，验证失败返回 None。
        """
        self.required_permissions = required_permissions or []
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        x_api_key: str | None = Header(None, alias="X-Api-Key", description="API 密钥"),
    ) -> ExchangeApiKey | None:
        """验证 API 密钥"""
        if not x_api_key:
            if self.auto_error:
                raise HTTPException(status_code=401, detail="未提供 API 密钥")
            return None

        try:
            # 1. 验证密钥哈希
            key_hash = hash_api_key(x_api_key)
            api_key = await ExchangeApiKey.filter(key_hash=key_hash).first()

            if not api_key:
                logger.warning(f"无效的 API 密钥: {x_api_key[:8]}...")
                if self.auto_error:
                    raise HTTPException(status_code=401, detail="无效的 API 密钥")
                return None

            # 2. 检查是否启用
            if not api_key.is_active:
                logger.warning(f"API 密钥已禁用: {api_key.name}")
                if self.auto_error:
                    raise HTTPException(status_code=401, detail="API 密钥已被禁用")
                return None

            # 3. 检查过期时间
            if api_key.expires_at:
                now = datetime.now(tz=UTC)
                expires = api_key.expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=UTC)

                if expires < now:
                    logger.warning(f"API 密钥已过期: {api_key.name}")
                    if self.auto_error:
                        raise HTTPException(status_code=401, detail="API 密钥已过期")
                    return None

            # 4. 验证 IP 白名单
            if api_key.ip_whitelist:
                client_ip = get_client_ip(request)
                if client_ip not in api_key.ip_whitelist:
                    logger.warning(f"IP 不在白名单中: {client_ip}, 密钥: {api_key.name}")
                    if self.auto_error:
                        raise HTTPException(status_code=403, detail="IP 地址不在白名单中")
                    return None

            # 5. 检查权限
            if self.required_permissions:
                missing = [p for p in self.required_permissions if p not in api_key.permissions]
                if missing:
                    logger.warning(f"缺少权限: {missing}, 密钥: {api_key.name}")
                    if self.auto_error:
                        raise HTTPException(status_code=403, detail=f"缺少权限: {', '.join(missing)}")
                    return None

            # 6. 检查速率限制
            rate_limiter = get_rate_limiter()
            is_allowed, current_count, remaining = await rate_limiter.is_allowed(
                key=f"api_key:{api_key.id}", limit=api_key.rate_limit, window_seconds=60
            )

            if not is_allowed:
                logger.warning(f"速率限制超出: {api_key.name}, {current_count}/{api_key.rate_limit}")
                if self.auto_error:
                    raise HTTPException(
                        status_code=429,
                        detail=f"请求频率超出限制 ({api_key.rate_limit}/分钟)",
                        headers={
                            "X-RateLimit-Limit": str(api_key.rate_limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": "60",
                        },
                    )
                return None

            # 7. 原子更新使用信息，避免并发计数丢失
            from tortoise.expressions import F

            await ExchangeApiKey.filter(id=api_key.id).update(
                last_used_at=datetime.now(tz=UTC),
                usage_count=F("usage_count") + 1,
            )

            # 记录认证状态，供后续权限系统使用
            request.state.is_api_key_auth = True
            request.state.api_key = api_key

            return api_key

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API 密钥验证失败: {e}")
            if self.auto_error:
                raise HTTPException(status_code=500, detail="认证服务异常")
            return None


def get_client_ip(request: Request) -> str:
    """获取客户端 IP（供其他地方使用）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


# 预定义的权限认证器
DependApiKeySend = ApiKeyAuth(required_permissions=["send"])
DependApiKeyReceive = ApiKeyAuth(required_permissions=["receive"])
DependApiKeySearch = ApiKeyAuth(required_permissions=["search"])
DependApiKeyDelete = ApiKeyAuth(required_permissions=["delete"])
DependApiKeyFolders = ApiKeyAuth(required_permissions=["folders"])
DependApiKeyDrafts = ApiKeyAuth(required_permissions=["drafts"])
DependApiKeySync = ApiKeyAuth(required_permissions=["sync"])
DependApiKeyRead = ApiKeyAuth(required_permissions=["read"])
DependApiKeyReply = ApiKeyAuth(required_permissions=["reply"])
DependApiKeyForward = ApiKeyAuth(required_permissions=["forward"])
DependApiKeyContact = ApiKeyAuth(required_permissions=["contacts"])
DependApiKeyAny = ApiKeyAuth()  # 任意有效密钥

# Webhook permissions
DependApiKeyWebhook = ApiKeyAuth(required_permissions=["webhook"])
# Optional webhook auth (supports both JWT user and API key callers)
OptionalApiKeyWebhook = ApiKeyAuth(required_permissions=["webhook"], auto_error=False)


def verify_account_access(api_key: ExchangeApiKey, account_id: int) -> None:
    """
    Raise HTTP 403 if *api_key* is not allowed to operate on *account_id*.

    An empty ``allowed_accounts`` list means the key has access to **all**
    accounts.  Use this helper in every route handler instead of repeating
    the same three-line check inline.
    """
    if api_key.allowed_accounts and account_id not in api_key.allowed_accounts:
        raise HTTPException(status_code=403, detail="API key is not authorised for this account")
