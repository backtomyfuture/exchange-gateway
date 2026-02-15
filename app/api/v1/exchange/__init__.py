"""
Exchange API 模块
"""
from fastapi import APIRouter

from .emails import router as emails_router
from .accounts import router as accounts_router
from .api_keys import router as api_keys_router
from .templates import router as templates_router
from .health import router as health_router

exchange_router = APIRouter()

# 健康检查（无需认证）
exchange_router.include_router(health_router, tags=["Exchange - 健康检查"])

# 邮件操作（使用 API Key 认证）
exchange_router.include_router(emails_router, prefix="/emails", tags=["Exchange - 邮件操作"])

# 账户管理（使用 JWT 认证）
exchange_router.include_router(accounts_router, prefix="/accounts", tags=["Exchange - 账户管理"])

# API 密钥管理（使用 JWT 认证）
exchange_router.include_router(api_keys_router, prefix="/api-keys", tags=["Exchange - API密钥"])

# 模板管理（使用 JWT 认证）
exchange_router.include_router(templates_router, prefix="/templates", tags=["Exchange - 邮件模板"])

from .contacts import router as contacts_router
# 联系人查询（使用 API Key 认证）
exchange_router.include_router(contacts_router, prefix="/contacts", tags=["Exchange - 通讯录"])

