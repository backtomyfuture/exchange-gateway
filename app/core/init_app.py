from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from tortoise.expressions import Q

from app.api import api_router
from app.api.v1.health import router as health_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    EWSGatewayException,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
    ews_exception_handler,
)
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.settings.config import settings

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware, RequestIDMiddleware


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(RequestIDMiddleware),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/docs",
                "/openapi.json",
                "/health",
                "/health/live",
                "/health/ready",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)
    app.add_exception_handler(EWSGatewayException, ews_exception_handler)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)
    app.include_router(health_router, prefix="/health", tags=["健康检查"])


async def init_superuser():
    """初始化超级用户，使用异常处理避免多 worker 竞态条件。"""
    from tortoise.exceptions import IntegrityError

    try:
        await user_controller.create_user(
            UserCreate(
                username="admin",
                email="admin@admin.com",
                password="123456",
                is_active=True,
                is_superuser=True,
            )
        )
    except IntegrityError:
        pass


async def init_menus():
    """初始化菜单，使用 update_or_create 保证幂等和并发安全。"""

    async def upsert_catalog(name: str, path: str, order: int, icon: str, redirect: str) -> Menu:
        catalog, _ = await Menu.update_or_create(
            defaults={
                "menu_type": MenuType.CATALOG,
                "path": path,
                "order": order,
                "icon": icon,
                "is_hidden": False,
                "component": "Layout",
                "keepalive": False,
                "redirect": redirect,
            },
            name=name,
            parent_id=0,
        )
        return catalog

    async def upsert_child(parent_id: int, child: dict) -> None:
        await Menu.update_or_create(
            defaults={
                "menu_type": MenuType.MENU,
                "path": child["path"],
                "order": child["order"],
                "icon": child["icon"],
                "is_hidden": False,
                "component": child["component"],
                "keepalive": False,
            },
            name=child["name"],
            parent_id=parent_id,
        )

    # 1. 邮件服务
    exchange_menu = await upsert_catalog(
        name="邮件服务",
        path="/exchange",
        order=2,
        icon="ph:envelope-simple-open-bold",
        redirect="/exchange/accounts",
    )

    exchange_children = [
        {
            "name": "账户管理",
            "path": "accounts",
            "component": "/exchange/accounts",
            "icon": "material-symbols:contact-mail-outline",
            "order": 1,
        },
        {
            "name": "API密钥",
            "path": "keys",
            "component": "/exchange/keys",
            "icon": "material-symbols:key-outline",
            "order": 2,
        },
        {
            "name": "Webhook 订阅",
            "path": "webhooks",
            "component": "/exchange/webhooks",
            "icon": "mdi:webhook",
            "order": 3,
        },
        {
            "name": "邮件模板",
            "path": "templates",
            "component": "/exchange/templates",
            "icon": "material-symbols:article-outline",
            "order": 4,
        },
        {
            "name": "操作日志",
            "path": "logs",
            "component": "/exchange/logs",
            "icon": "material-symbols:history",
            "order": 5,
        },
        {
            "name": "使用统计",
            "path": "stats",
            "component": "/exchange/stats",
            "icon": "material-symbols:analytics-outline",
            "order": 6,
        },
        {
            "name": "开发者指南",
            "path": "developer",
            "component": "/developer",
            "icon": "material-symbols:help-outline",
            "order": 7,
        },
    ]

    for child in exchange_children:
        await upsert_child(exchange_menu.id, child)

    # 2. 系统管理
    system_menu = await upsert_catalog(
        name="系统管理",
        path="/system",
        order=1,
        icon="carbon:gui-management",
        redirect="/system/user",
    )

    system_children = [
        {
            "name": "用户管理",
            "path": "user",
            "order": 1,
            "icon": "material-symbols:person-outline-rounded",
            "component": "/system/user",
        },
        {"name": "角色管理", "path": "role", "order": 2, "icon": "carbon:user-role", "component": "/system/role"},
        {
            "name": "菜单管理",
            "path": "menu",
            "order": 3,
            "icon": "material-symbols:list-alt-outline",
            "component": "/system/menu",
        },
        {"name": "API管理", "path": "api", "order": 4, "icon": "ant-design:api-outlined", "component": "/system/api"},
        {
            "name": "部门管理",
            "path": "dept",
            "order": 5,
            "icon": "mingcute:department-line",
            "component": "/system/dept",
        },
        {
            "name": "审计日志",
            "path": "auditlog",
            "order": 6,
            "icon": "ph:clipboard-text-bold",
            "component": "/system/auditlog",
        },
    ]

    for child in system_children:
        await upsert_child(system_menu.id, child)


async def init_apis():
    await api_controller.refresh_api()


async def _run_migrations():
    """执行 Aerich 迁移并同步 schema。"""
    try:
        from aerich import Command

        command = Command(tortoise_config=settings.TORTOISE_ORM, app="models")
        await command.init()
        await command.upgrade()
        await Tortoise.generate_schemas(safe=True)
        logger.info("数据库迁移已成功应用")
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        try:
            await Tortoise.generate_schemas(safe=True)
            logger.info("Schema 同步完成（safe 模式）")
        except Exception as se:
            logger.critical(f"数据库初始化失败: {se}")
            raise


async def init_db():
    """
    初始化数据库表
    使用 Redis 分布式锁确保只有一个 worker 执行迁移
    """
    import os

    auto_migrate = os.getenv("AUTO_MIGRATE", "true").lower() in ("true", "1", "yes")
    await Tortoise.init(config=settings.TORTOISE_ORM)

    if not auto_migrate:
        logger.info("AUTO_MIGRATE=false，跳过启动迁移")
        return

    # 尝试通过 Redis 分布式锁协调多 worker 迁移
    try:
        import redis.asyncio as aioredis

        from app.utils.migration_lock import MigrationLock

        redis_client = aioredis.from_url(settings.REDIS_URL)
        lock = MigrationLock(redis_client)

        if await lock.acquire():
            try:
                await _run_migrations()
            finally:
                await lock.release()
        else:
            await lock.wait_for_completion()

        await redis_client.aclose()
    except Exception as e:
        logger.warning(f"Redis 锁不可用，直接执行迁移: {e}")
        await _run_migrations()


async def init_roles():
    """初始化角色，使用异常处理避免多 worker 竞态条件。"""
    try:
        admin_role = await Role.create(
            name="管理员",
            desc="管理员角色",
        )
    except IntegrityError:
        admin_role = await Role.get(name="管理员")

    try:
        user_role = await Role.create(
            name="普通用户",
            desc="普通用户角色",
        )
    except IntegrityError:
        user_role = await Role.get(name="普通用户")

    try:
        all_apis = await Api.all()
        await admin_role.apis.add(*all_apis)
    except Exception as e:
        logger.warning(f"Failed to assign APIs to admin role: {e}")

    try:
        all_menus = await Menu.all()
        await admin_role.menus.add(*all_menus)
    except Exception as e:
        logger.warning(f"Failed to assign menus to admin role: {e}")

    try:
        await user_role.menus.add(*all_menus)
    except Exception as e:
        logger.warning(f"Failed to assign menus to user role: {e}")

    try:
        basic_apis = await Api.filter(Q(method__in=["GET"]) | Q(tags="基础模块"))
        await user_role.apis.add(*basic_apis)
    except Exception as e:
        logger.warning(f"Failed to assign basic APIs to user role: {e}")


async def init_data():
    await init_db()
    await init_superuser()
    await init_menus()
    await init_apis()
    await init_roles()
    # 初始化 Redis 速率限制器
    from app.core.redis_rate_limiter import init_rate_limiter

    await init_rate_limiter()
