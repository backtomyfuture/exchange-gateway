from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()

    # 恢复未完成的邮件发送任务
    try:
        from app.services.exchange.email_service import recover_pending_emails
        await recover_pending_emails()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"邮件任务恢复失败: {e}")


    

    yield

    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": f"Welcome to {settings.APP_TITLE}",
            "status": "running",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health"
        }

    return app


app = create_app()
