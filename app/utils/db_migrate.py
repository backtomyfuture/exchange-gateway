#!/usr/bin/env python3
"""
独立数据库迁移脚本
可用于容器首次启动前手动执行迁移

用法:
    # 开发环境 (使用默认配置)
    python -m app.utils.db_migrate

    # 生产环境 (需要设置环境变量)
    export DB_HOST=mysql
    export DB_PORT=3306
    export DB_USER=root
    export DB_PASSWORD=your_password
    export DB_NAME=vue_fastapi_admin
    python -m app.utils.db_migrate
"""

import asyncio
import os
import sys
from urllib.parse import urlparse


def parse_database_url(database_url: str) -> dict:
    """Parse DATABASE_URL into connection parameters."""
    parsed = urlparse(database_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") if parsed.path else "exchange_gateway",
    }


def get_tortoise_config():
    """
    构建独立的 Tortoise ORM 配置
    不依赖 app.settings，避免验证逻辑阻止启动
    """
    # 优先解析 MYSQL_URL / DATABASE_URL
    database_url = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

    # 从分离的组件 + secret 文件构建
    if not database_url:
        host = os.getenv("DB_HOST", "")
        if host:
            port = os.getenv("DB_PORT", "3306")
            name = os.getenv("DB_NAME", "exchange_gateway")
            user = os.getenv("DB_USER", "root")
            pw_file = os.getenv("DB_PASSWORD_FILE", "")
            pw = ""
            if pw_file:
                try:
                    with open(pw_file) as f:
                        pw = f.read().strip()
                except FileNotFoundError:
                    pass
            if not pw:
                pw = os.getenv("DB_PASSWORD", "")
            database_url = f"mysql://{user}:{pw}@{host}:{port}/{name}"

    # DEV_MODE fallback
    if not database_url:
        dev_mode = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
        if dev_mode:
            database_url = "mysql://root:dev_password@localhost:3306/exchange_gateway"
        else:
            print("ERROR: Set DATABASE_URL or DB_HOST+DB_PASSWORD_FILE")
            sys.exit(1)

    # 动态检测引擎
    if database_url.lower().startswith("postgres"):
        db_engine = "tortoise.backends.asyncpg"
        db_conn_name = "postgres"
    else:
        db_engine = "tortoise.backends.mysql"
        db_conn_name = "mysql"

    # 解析参数
    db_params = parse_database_url(database_url)

    return {
        "connections": {
            db_conn_name: {
                "engine": db_engine,
                "credentials": {
                    "host": db_params["host"],
                    "port": db_params["port"],
                    "user": db_params["user"],
                    "password": db_params["password"],
                    "database": db_params["database"],
                    "minsize": 5,
                    "maxsize": 20,
                    "charset": "utf8mb4" if "mysql" in db_engine else None,
                },
            },
        },
        "apps": {
            "models": {
                "models": [
                    "app.models.admin",
                    "app.models.exchange",
                    "app.models.webhook",
                    "aerich.models",
                ],
                "default_connection": db_conn_name,
            },
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }


async def run_migration():
    """执行数据库迁移"""
    print("=" * 50)
    print("Starting database migration...")
    print("=" * 50)

    # 从环境变量构建配置
    tortoise_config = get_tortoise_config()

    # 获取配置中的数据库连接参数进行打印
    # 动态获取第一个连接的名称
    first_conn_name = next(iter(tortoise_config["connections"]))
    creds = tortoise_config["connections"][first_conn_name]["credentials"]

    # 构造显示的 URL (隐藏密码)
    # 不再尝试从配置中读取 'url'，而是从 get_tortoise_config 解析出的参数重组
    scheme = "postgres" if "postgres" in tortoise_config["connections"][first_conn_name]["engine"] else "mysql"
    user = creds.get("user", "root")
    host = creds.get("host", "localhost")
    port = creds.get("port", 3306)
    database = creds.get("database", "exchange_gateway")

    safe_url = f"{scheme}://{user}:****@{host}:{port}/{database}"
    print(f"Database URL: {safe_url}")
    print()

    # 初始化 Tortoise ORM
    from tortoise import Tortoise

    print("Initializing Tortoise ORM...")
    await Tortoise.init(config=tortoise_config)
    print("  - Tortoise ORM initialized")

    # 执行迁移（使用 Aerich）
    print("Applying database migrations via Aerich...")
    try:
        from aerich import Command

        command = Command(tortoise_config=tortoise_config, app="models")
        await command.init()
        await command.upgrade()
        print("  - Database migrations applied successfully")
    except Exception as e:
        print(f"  - Migration failed or unnecessary: {e}")
        # 只有在非常极端的情况下才回退到 generate_schemas
        print("Falling back to schema sync (safe mode)...")
        try:
            await Tortoise.generate_schemas(safe=True)
            print("  - Schema sync completed")
        except Exception as se:
            print(f"  - Schema sync failed: {se}")

    print()
    print("=" * 50)
    print("Database initialization completed!")
    print("=" * 50)

    # 关闭连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_migration())
