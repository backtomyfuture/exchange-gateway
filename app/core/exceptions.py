from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError


class SettingNotFoundError(Exception):
    pass


SettingNotFound = SettingNotFoundError


async def does_not_exist_handle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        code=404,
        msg="请求的资源不存在",
    )
    return JSONResponse(content=content, status_code=404)


DoesNotExistHandle = does_not_exist_handle


async def integrity_handle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        code=500,
        msg="数据完整性错误，请检查是否存在重复或关联数据冲突",
    )
    return JSONResponse(content=content, status_code=500)


IntegrityHandle = integrity_handle


async def http_exc_handle(_: Request, exc: HTTPException) -> JSONResponse:
    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


HttpExcHandle = http_exc_handle


async def request_validation_handle(_: Request, exc: RequestValidationError) -> JSONResponse:
    content = dict(code=422, msg="请求参数验证失败", data=exc.errors())
    return JSONResponse(content=content, status_code=422)


RequestValidationHandle = request_validation_handle


async def response_validation_handle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    content = dict(code=500, msg="服务端响应数据异常")
    return JSONResponse(content=content, status_code=500)


ResponseValidationHandle = response_validation_handle


# =============================================================================
# Domain Exception Hierarchy
# =============================================================================


class EWSGatewayError(Exception):
    """Base class for all exchange-gateway domain exceptions."""

    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


EWSGatewayException = EWSGatewayError


class AccountNotFoundError(EWSGatewayError):
    error_code = "ACCOUNT_NOT_FOUND"
    http_status = 404


class AccountDisabledError(EWSGatewayError):
    error_code = "ACCOUNT_DISABLED"
    http_status = 403


class InvalidCredentialsError(EWSGatewayError):
    error_code = "INVALID_CREDENTIALS"
    http_status = 401


class ExchangeConnectionError(EWSGatewayError):
    error_code = "EXCHANGE_CONNECTION_ERROR"
    http_status = 503


class ExchangeTimeoutError(EWSGatewayError):
    error_code = "EXCHANGE_TIMEOUT"
    http_status = 504


class AttachmentTooLargeError(EWSGatewayError):
    error_code = "ATTACHMENT_TOO_LARGE"
    http_status = 413


class ExchangeAuthError(EWSGatewayError):
    error_code = "EXCHANGE_AUTH_FAILED"
    http_status = 502


class TemplateRenderError(EWSGatewayError):
    error_code = "TEMPLATE_RENDER_ERROR"
    http_status = 422


class GatewayCircuitOpenError(EWSGatewayError):
    error_code = "CIRCUIT_OPEN"
    http_status = 503


class WebhookDeliveryError(EWSGatewayError):
    error_code = "WEBHOOK_DELIVERY_ERROR"
    http_status = 502


class EmailNotFoundError(EWSGatewayError):
    error_code = "EMAIL_NOT_FOUND"
    http_status = 404


async def ews_exception_handler(request: Request, exc: EWSGatewayError) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error_code": exc.error_code,
            "message": exc.message or str(exc),
            "request_id": request_id,
        },
    )
