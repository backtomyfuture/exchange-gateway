"""
ARQ Worker entry point for exchange-gateway.

Run with:  python -m arq app.tasks.worker.WorkerSettings
"""

import asyncio
import time
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from tortoise import Tortoise

from app.settings import settings
from app.tasks.cleanup_tasks import cleanup_sensitive_logs_task
from app.tasks.email_tasks import send_email_task
from app.tasks.webhook_tasks import deliver_webhook_task, ping_all_accounts_task


async def _heartbeat_loop(path: str = "/tmp/worker_heartbeat") -> None:
    """Periodically prove that the ARQ event loop is still making progress."""
    heartbeat = Path(path)
    while True:
        heartbeat.write_text(str(time.time()), encoding="utf-8")
        await asyncio.sleep(10)


async def startup(ctx: dict) -> None:
    """Initialize Tortoise ORM for the ARQ worker process."""
    from app.settings import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)
    ctx["db_initialized"] = True
    ctx["heartbeat_task"] = asyncio.create_task(_heartbeat_loop())


async def shutdown(ctx: dict) -> None:
    """Close Tortoise ORM connections."""
    heartbeat_task = ctx.get("heartbeat_task")
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    await Tortoise.close_connections()


class WorkerSettings:
    functions = [send_email_task, deliver_webhook_task]
    cron_jobs = [
        cron(ping_all_accounts_task, minute=set(range(0, 60, 5))),  # Every 5 min
        cron(cleanup_sensitive_logs_task, hour=2, minute=0),  # Daily at 02:00
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results 1 hour for debugging
    retry_jobs = True
    queue_name = "exchange-gateway"
