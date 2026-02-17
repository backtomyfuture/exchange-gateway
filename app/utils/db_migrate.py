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


def get_tortoise_config():
    """
    构建独立的 Tortoise ORM 配置
    不依赖 app.settings，避免验证逻辑阻止启动
    """
    # 优先解析 MYSQL_URL / DATABASE_URL
    database_url = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")
    
    # DEV_MODE 默认值
    if not database_url:
        dev_mode = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
        if dev_mode:
            database_url = "mysql://root:dev_password@localhost:3306/exchange_gateway"
        else:
            print("ERROR: DATABASE_URL or MYSQL_URL must be set in production")
            sys.exit(1)

    # 动态检测引擎
    db_engine = "tortoise.backends.asyncpg" if database_url.lower().startswith("postgres") else "tortoise.backends.mysql"

    return {
        "connections": {
            "default": {
                "engine": db_engine,
                "credentials": {
                    "url": database_url,
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
                "default_connection": "default",
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

    # 打印配置信息（不包含密码）
    db_url = tortoise_config['connections']['default']['credentials']['url']
    # 隐藏密码进行打印
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(db_url)
    # 构造安全 URL (隐藏密码)
    netloc = f"{parsed.username}:****@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    safe_url = urlunparse(parsed._replace(netloc=netloc))
    print(f"Database URL: {safe_url}")
    print()

    # 初始化 Tortoise ORM
    from tortoise import Tortoise

    print("Initializing Tortoise ORM...")
    await Tortoise.init(config=tortoise_config)
    print("  - Tortoise ORM initialized")

    # 生成架构（创建所有表）
    print("Generating database schema...")
    try:
        await Tortoise.generate_schemas()
        print("  - Schema generated successfully")
    except Exception as e:
        print(f"  - Schema generation warning: {e}")

    print()
    print("=" * 50)
    print("Database migration completed!")
    print("=" * 50)

    # 关闭连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_migration())
