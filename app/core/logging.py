"""Structured logging configuration using structlog.

Production (ENV=prod): JSON output for log aggregation.
Development (ENV=dev): Colored human-readable console output.

New code should prefer:
    from app.core.logging import get_logger
    log = get_logger(__name__)
    log.info("event happened", key="value")

Existing code using loguru via `from app.log import logger` continues to work.
The request_id context is shared via structlog.contextvars and can be injected
into loguru via `from structlog.contextvars import get_contextvars`.
"""

import logging
import sys

import structlog

from app.settings import settings
from app.settings.config import ENV


def configure_logging() -> None:
    """Configure structlog. Call once at application startup."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Injects request_id automatically
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if ENV == "prod":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure structlog's stdlib bridge (does not override loguru)
    structlog_root = logging.getLogger("structlog")
    structlog_root.handlers = [handler]
    structlog_root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    structlog_root.propagate = False

    # 捕获根 logger，使第三方库（exchangelib、tortoise、uvicorn）也通过 structlog 输出
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


def get_logger(name: str):
    """Get a structlog logger. Prefer this over loguru for new code."""
    return structlog.get_logger(name)
