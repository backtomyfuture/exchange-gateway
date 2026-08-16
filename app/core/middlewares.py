import re
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.models.admin import AuditLog, User

from .bgtask import BgTasks

# Request ID 上下文变量
CTX_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")

_audit_logger = structlog.get_logger("audit")

# 敏感字段集合，用于审计日志脱敏
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "key",
        "api_key",
        "x_api_key",
        "encrypted_password",
        "secret_key",
        "encryption_key",
        "authorization",
        "credential",
        "credentials",
    }
)


def _mask_sensitive(data: Any) -> Any:
    """递归脱敏日志数据中的敏感字段，支持字典和顶层列表。"""
    if isinstance(data, dict):
        return {key: "***" if key.lower() in _SENSITIVE_KEYS else _mask_sensitive(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_mask_sensitive(item) for item in data]
    return data


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class RequestIDMiddleware(SimpleBaseMiddleware):
    """
    Request ID 中间件
    为每个请求生成唯一标识，便于日志追踪和问题排查
    """

    async def before_request(self, request: Request):
        # 优先使用客户端传入的 Request ID（如通过网关传入）
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        CTX_REQUEST_ID.set(request_id)
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

    async def after_request(self, request: Request):
        structlog.contextvars.clear_contextvars()


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths

    async def get_request_log(self, request: Request, response: Any) -> dict:
        """根据request和response对象获取对应的日志记录数据"""
        data: dict = {
            "path": request.url.path,
            "status": response.status_code,
            "method": request.method,
            "module": "",
            "summary": request.url.path,
        }
        # 路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags) if route.tags else ""
                data["summary"] = route.summary or route.path_format or ""
        # 从 request.state 获取已认证的用户信息，避免重复解析 token
        user_id = 0
        username = ""
        try:
            from app.core.ctx import CTX_USER_ID

            user_id = CTX_USER_ID.get(0)
            if user_id:
                user_obj = await User.filter(id=user_id).first()
                if user_obj:
                    username = user_obj.username
        except Exception:
            pass
        data["user_id"] = user_id
        data["username"] = username
        data["request_id"] = getattr(request.state, "request_id", None) or CTX_REQUEST_ID.get() or None
        return data

    async def before_request(self, request: Request):
        # Deliberately do not read the request body. Mail bodies and attachments
        # must never enter the general HTTP audit trail.
        return None

    async def after_request(self, request: Request, response: Response, process_time: int):
        if request.method in self.methods:
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I) is not None:
                    return
            data: dict = await self.get_request_log(request=request, response=response)
            data["response_time"] = process_time
            # Keep the legacy columns for schema compatibility, but never
            # populate them with request or response content.
            data["request_args"] = None
            data["response_body"] = None
            try:
                await AuditLog.create(**data)
            except Exception as e:
                _audit_logger.warning("Failed to write audit log", error=str(e))

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time: datetime = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time: datetime = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        return response
