from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q
from tortoise import Tortoise

from app.api import api_router
from app.api.v1.health import router as health_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
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
        Middleware(RequestIDMiddleware),  # Request ID 追踪
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


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)
    # 健康检查端点（不需要认证，在根路径）
    app.include_router(health_router, prefix="/health", tags=["健康检查"])


async def init_superuser():
    """
    初始化超级用户
    使用异常处理避免多 worker 竞态条件
    """
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
        # 用户已存在，多 worker 竞态条件，忽略
        pass


async def init_menus():
    """
    初始化菜单
    使用异常处理避免多 worker 竞态条件和重复数据问题
    """
    from tortoise.exceptions import MultipleObjectsReturned

    # 1. 邮件服务 (作为首选菜单)
    # 尝试获取及其ID，以支持幂等性
    try:
        exchange_menu = await Menu.get(name="邮件服务")
    except MultipleObjectsReturned:
        # 存在重复数据，删除后重新获取第一个
        duplicates = await Menu.filter(name="邮件服务").all()
        for dup in duplicates[1:]:
            await dup.delete()
        exchange_menu = await Menu.get(name="邮件服务")
    except Exception:
        # 菜单不存在，创建新菜单
        exchange_menu = None

    if not exchange_menu:
        try:
            exchange_menu = await Menu.create(
                menu_type=MenuType.CATALOG,
                name="邮件服务",
                path="/exchange",
                order=2,  # 邮件服务
                parent_id=0,
                icon="ph:envelope-simple-open-bold",
                is_hidden=False,
                component="Layout",
                keepalive=False,
                redirect="/exchange/accounts",
            )
        except IntegrityError:
            # 竞态条件，忽略
            exchange_menu = await Menu.get(name="邮件服务")

    # 检查并创建子菜单
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
            "name": "Webhook订阅",
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
    ]

    for child in exchange_children:
        if not await Menu.filter(name=child["name"], parent_id=exchange_menu.id).exists():
            await Menu.create(
                menu_type=MenuType.MENU,
                name=child["name"],
                path=child["path"],
                order=child["order"],
                parent_id=exchange_menu.id,
                icon=child["icon"],
                is_hidden=False,
                component=child["component"],
                keepalive=False,
            )

    # 2. 系统管理
    if not await Menu.filter(name="系统管理").exists():
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)

    # 3. 开发者服务
    if not await Menu.filter(name="开发者服务").exists():
        dev_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="开发者服务",
            path="/developer",
            order=3,
            parent_id=0,
            icon="material-symbols:code",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/developer/index",
        )
        dev_children = [
            Menu(
                menu_type=MenuType.MENU,
                name="开发者指南",
                path="index",
                order=1,
                parent_id=dev_menu.id,
                icon="material-symbols:help-outline",
                is_hidden=False,
                component="/developer",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(dev_children)


async def init_apis():
    await api_controller.refresh_api()


async def init_db():
    """
    初始化数据库表
    使用 Tortoise.generate_schemas() 直接从模型创建表，更可靠
    """
    import os
    from tortoise import Tortoise

    # 检查是否启用启动时迁移
    auto_migrate = os.getenv("AUTO_MIGRATE", "true").lower() in ("true", "1", "yes")
    if not auto_migrate:
        logger.info("AUTO_MIGRATE=false, skipping startup migration")
        await Tortoise.init(config=settings.TORTOISE_ORM)
        return

    await Tortoise.init(config=settings.TORTOISE_ORM)

    # 使用 Tortoise.generate_schemas() 直接从模型创建表
    try:
        await Tortoise.generate_schemas()
        logger.info("Database schema generated successfully")
    except Exception as e:
        # 表可能已存在，尝试继续
        logger.warning(f"Schema generation warning: {e}")


async def init_roles():
    """
    初始化角色
    使用异常处理避免多 worker 竞态条件
    """
    # 创建管理员角色（处理重复）
    try:
        admin_role = await Role.create(
            name="管理员",
            desc="管理员角色",
        )
    except IntegrityError:
        admin_role = await Role.get(name="管理员")

    # 创建普通用户角色（处理重复）
    try:
        user_role = await Role.create(
            name="普通用户",
            desc="普通用户角色",
        )
    except IntegrityError:
        user_role = await Role.get(name="普通用户")

    # 始终确保管理员拥有所有API和菜单
    all_apis = await Api.all()
    await admin_role.apis.add(*all_apis)

    all_menus = await Menu.all()
    await admin_role.menus.add(*all_menus)

    # 始终确保普通用户拥有所有菜单（根据需求）和基础API
    await user_role.menus.add(*all_menus)
    basic_apis = await Api.filter(Q(method__in=["GET"]) | Q(tags="基础模块"))
    await user_role.apis.add(*basic_apis)


async def init_data():
    await init_db()
    await init_superuser()
    await init_menus()
    await init_apis()
    await init_roles()
