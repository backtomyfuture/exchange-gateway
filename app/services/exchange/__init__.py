"""
Exchange 服务模块
"""
from .connection_pool import ExchangeConnectionPool, get_exchange_connection, get_connection_pool
from .email_service import EmailService, get_email_service
from .account_service import AccountService, get_account_service
from .template_service import TemplateService, get_template_service
from .audit_service import AuditService, get_audit_service

__all__ = [
    "ExchangeConnectionPool",
    "get_exchange_connection",
    "get_connection_pool",
    "EmailService",
    "get_email_service",
    "AccountService",
    "get_account_service",
    "TemplateService",
    "get_template_service",
    "AuditService",
    "get_audit_service",
]

