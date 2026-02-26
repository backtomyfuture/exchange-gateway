from typing import Optional

import jwt
import structlog
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.models import ExchangeApiKey, Role, User
from app.settings import settings
from app.utils.crypto import hash_api_key

logger = structlog.get_logger(__name__)


def extract_token(token: str) -> str:
    """
    从 token 字符串中提取实际的 JWT token
    支持以下格式：
    - 直接的 token 字符串
    - Bearer token 格式（如：Bearer xxx）
    """
    if token.lower().startswith("bearer "):
        return token[7:].strip()
    return token


class AuthControl:
    @classmethod
    async def is_authed(
        cls,
        request: Request,
        token: str = Header(None, description="token验证"),
        authorization: str = Header(None, description="Authorization Bearer token"),
    ) -> Optional["User"]:
        # 0. 优先尝试 API Key 认证
        x_api_key = request.headers.get("X-Api-Key")
        if x_api_key:
            try:
                key_hash = hash_api_key(x_api_key)
                api_key = await ExchangeApiKey.filter(key_hash=key_hash, is_active=True).first()
                if api_key:
                    request.state.is_api_key_auth = True
                    request.state.api_key = api_key
                    return None
            except Exception:
                pass

        if getattr(request.state, "is_api_key_auth", False):
            return None

        # 支持两种 token 传递方式：token header 或 Authorization Bearer
        actual_token = token or authorization
        if not actual_token:
            raise HTTPException(status_code=401, detail="未提供认证 Token")

        actual_token = extract_token(actual_token)
        try:
            if actual_token == "dev":
                if not settings.DEBUG:
                    raise HTTPException(status_code=401, detail="Dev token is disabled in production")
                logger.warning("使用 dev token 登录，仅限开发环境使用")
                user = await User.filter().first()
                if not user:
                    raise HTTPException(status_code=401, detail="No user found for dev token")
                user_id = user.id
            else:
                decode_data = jwt.decode(actual_token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            CTX_USER_ID.set(int(user_id))
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication error", error=repr(e))
            raise HTTPException(status_code=500, detail="认证服务内部错误")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if getattr(request.state, "is_api_key_auth", False):
            return

        if current_user.is_superuser:
            return
        method = request.method
        route = request.scope.get("route")
        path = getattr(route, "path_format", getattr(route, "path", request.url.path))
        roles: list[Role] = await current_user.roles.all().prefetch_related("apis")
        if not roles:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        permission_apis = {(api.method, api.path) for role in roles for api in role.apis}
        if (method, path) not in permission_apis:
            logger.warning("Permission denied", method=method, path=path, roles=[r.name for r in roles])
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
