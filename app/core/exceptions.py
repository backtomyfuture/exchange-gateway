from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError


class SettingNotFound(Exception):
    pass


async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        code=404,
        msg=f"Object has not found, exc: {exc}, query_params: {req.query_params}",
    )
    return JSONResponse(content=content, status_code=404)


async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        code=500,
        msg=f"IntegrityError，{exc}",
    )
    return JSONResponse(content=content, status_code=500)


async def HttpExcHandle(_: Request, exc: HTTPException) -> JSONResponse:
    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


async def RequestValidationHandle(_: Request, exc: RequestValidationError) -> JSONResponse:
    content = dict(code=422, msg=f"RequestValidationError, {exc}")
    return JSONResponse(content=content, status_code=422)


async def ResponseValidationHandle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    content = dict(code=500, msg=f"ResponseValidationError, {exc}")
    return JSONResponse(content=content, status_code=500)


# =============================================================================
# Domain Exception Hierarchy
# =============================================================================

class EWSGatewayException(Exception):
    """Base class for all exchange-gateway domain exceptions."""
    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class AccountNotFoundError(EWSGatewayException):
    error_code = "ACCOUNT_NOT_FOUND"
    http_status = 404


class AccountDisabledError(EWSGatewayException):
    error_code = "ACCOUNT_DISABLED"
    http_status = 403


class InvalidCredentialsError(EWSGatewayException):
    error_code = "INVALID_CREDENTIALS"
    http_status = 401


class ExchangeConnectionError(EWSGatewayException):
    error_code = "EXCHANGE_CONNECTION_ERROR"
    http_status = 503


class ExchangeTimeoutError(EWSGatewayException):
    error_code = "EXCHANGE_TIMEOUT"
    http_status = 504


class ExchangeAuthError(EWSGatewayException):
    error_code = "EXCHANGE_AUTH_FAILED"
    http_status = 502


class TemplateRenderError(EWSGatewayException):
    error_code = "TEMPLATE_RENDER_ERROR"
    http_status = 422


class GatewayCircuitOpenError(EWSGatewayException):
    error_code = "CIRCUIT_OPEN"
    http_status = 503


async def ews_exception_handler(request: Request, exc: EWSGatewayException) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error_code": exc.error_code,
            "message": exc.message or str(exc),
            "request_id": request_id,
        },
    )
