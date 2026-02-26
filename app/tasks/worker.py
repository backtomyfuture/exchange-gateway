"""
ARQ Worker entry point for exchange-gateway.

Run with:  python -m arq app.tasks.worker.WorkerSettings
"""

from arq import cron
from arq.connections import RedisSettings
from tortoise import Tortoise

from app.settings import settings
from app.tasks.email_tasks import send_email_task
from app.tasks.webhook_tasks import (
    deliver_webhook_task,
    ping_all_accounts_task,
    renew_subscriptions_task,
)


async def startup(ctx: dict) -> None:
    """Initialize Tortoise ORM for the ARQ worker process."""
    from app.settings import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)
    ctx["db_initialized"] = True


async def shutdown(ctx: dict) -> None:
    """Close Tortoise ORM connections."""
    await Tortoise.close_connections()


class WorkerSettings:
    functions = [send_email_task, deliver_webhook_task]
    cron_jobs = [
        cron(renew_subscriptions_task, minute={0, 30}),  # Every 30 min
        cron(ping_all_accounts_task, minute=set(range(0, 60, 5))),  # Every 5 min
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results 1 hour for debugging
    retry_jobs = True
    queue_name = "exchange-gateway"
