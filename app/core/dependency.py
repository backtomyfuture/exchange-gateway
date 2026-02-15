from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.models import Role, User, ExchangeApiKey
from app.settings import settings
from app.utils.crypto import hash_api_key


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
            # 验证 API Key
            try:
                key_hash = hash_api_key(x_api_key)
                api_key = await ExchangeApiKey.filter(key_hash=key_hash, is_active=True).first()
                if api_key:
                    # 简单验证通过，设置状态跳过 JWT 和 RBAC
                    # 详细的权限验证 (permissions, ip, rate_limit) 仍由 endpoint 的 DependApiKeyXxx 处理
                    request.state.is_api_key_auth = True
                    request.state.api_key = api_key
                    return None
            except Exception as e:
                # 验证出错（如 DB 连接失败），记录日志并继续尝试 JWT
                # from app.log import logger
                # logger.error(f"API Key allowed check failed: {e}")
                pass

        # 如果已经通过 API Key 认证，则跳过 JWT 认证 (Prevent double check if somehow set elsewhere)
        if getattr(request.state, "is_api_key_auth", False):
            return None
            
        # 支持两种 token 传递方式：token header 或 Authorization Bearer
        actual_token = token or authorization
        if not actual_token:
            raise HTTPException(status_code=401, detail="未提供认证 Token")
        
        # 提取实际的 token（去除 Bearer 前缀）
        actual_token = extract_token(actual_token)
        try:
            # dev token 仅在 DEBUG 模式下可用
            if actual_token == "dev":
                if not settings.DEBUG:
                    raise HTTPException(status_code=401, detail="Dev token is disabled in production")
                from app.log import logger
                logger.warning("⚠️ 使用 dev token 登录，仅限开发环境使用！")
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
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        # 如果已经通过 API Key 认证，则跳过系统权限检查
        if getattr(request.state, "is_api_key_auth", False):
            return
            
        if current_user.is_superuser:
            return
        method = request.method
        # path = request.url.path
        # Use route template (e.g. /api/v1/users/{id}) instead of resolved path
        route = request.scope.get("route")
        path = getattr(route, "path_format", getattr(route, "path", request.url.path))
        roles: list[Role] = await current_user.roles
        if not roles:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        apis = [await role.apis for role in roles]
        permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))
        # path = "/api/v1/auth/userinfo"
        # method = "GET"
        if (method, path) not in permission_apis:
            print(f"DEBUG: Permission denied. Request: {method} {path}", flush=True)
            print(f"DEBUG: User roles: {[r.name for r in roles]}", flush=True)
            print(f"DEBUG: Allowed APIs (sample): {permission_apis[:5]}...", flush=True)
            # Check if this path exists in DB at all to see if it's a mismatch
            match_candidates = [api for api in permission_apis if api[0] == method and (api[1] in path or path in api[1])]
            print(f"DEBUG: Similar paths in allowed list: {match_candidates}", flush=True)
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
