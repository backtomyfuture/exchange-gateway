import json
import re
import uuid
from collections.abc import AsyncGenerator
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
        return {
            key: "***" if key.lower() in _SENSITIVE_KEYS else _mask_sensitive(value)
            for key, value in data.items()
        }
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
        self.audit_log_paths = ["/api/v1/auditlog/list"]
        self.max_body_size = 1024 * 1024  # 1MB 响应体大小限制

    async def get_request_args(self, request: Request) -> dict:
        args = {}
        # 获取查询参数
        for key, value in request.query_params.items():
            args[key] = value

        # 获取请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                args.update(body)
            except json.JSONDecodeError:
                try:
                    body = await request.form()
                    for k, v in body.items():
                        if hasattr(v, "filename"):
                            args[k] = v.filename
                        elif isinstance(v, list) and v and hasattr(v[0], "filename"):
                            args[k] = [file.filename for file in v]
                        else:
                            args[k] = v
                except Exception:
                    pass

        return _mask_sensitive(args)

    async def get_response_body(self, request: Request, response: Response) -> Any:
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return {"code": 0, "msg": "Response too large to log", "data": None}

        if hasattr(response, "body"):
            body = response.body
        else:
            body_chunks = []
            async for chunk in response.body_iterator:
                if not isinstance(chunk, bytes):
                    chunk = chunk.encode(response.charset)
                body_chunks.append(chunk)

            response.body_iterator = self._async_iter(body_chunks)
            body = b"".join(body_chunks)

        if any(request.url.path.startswith(path) for path in self.audit_log_paths):
            try:
                data = self.lenient_json(body)
                if isinstance(data, dict):
                    data.pop("response_body", None)
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            item.pop("response_body", None)
                return data
            except Exception:
                return None

        return self.lenient_json(body)

    def lenient_json(self, v: Any) -> Any:
        if isinstance(v, str | bytes):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                pass
        return v

    async def _async_iter(self, items: list[bytes]) -> AsyncGenerator[bytes, None]:
        for item in items:
            yield item

    async def get_request_log(self, request: Request, response: Response) -> dict:
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
        return data

    async def before_request(self, request: Request):
        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    async def after_request(self, request: Request, response: Response, process_time: int):
        if request.method in self.methods:
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I) is not None:
                    return
            data: dict = await self.get_request_log(request=request, response=response)
            data["response_time"] = process_time

            data["request_args"] = request.state.request_args
            data["response_body"] = await self.get_response_body(request, response)
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
