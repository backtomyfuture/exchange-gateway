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


def get_tortoise_config():
    """
    构建独立的 Tortoise ORM 配置
    不依赖 app.settings，避免验证逻辑阻止启动
    """
    # 检查必要的数据库环境变量
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "3306"))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "vue_fastapi_admin")

    # DEV_MODE 时使用默认密码
    dev_mode = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
    if dev_mode and not db_password:
        db_password = "dev_password"

    if not db_password:
        print("WARNING: DB_PASSWORD not set, using empty password")

    return {
        "connections": {
            "mysql": {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": db_host,
                    "port": db_port,
                    "user": db_user,
                    "password": db_password,
                    "database": db_name,
                    "minsize": 5,
                    "maxsize": 20,
                    "charset": "utf8mb4",
                },
            },
        },
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "mysql",
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
    print(f"DB Host: {tortoise_config['connections']['mysql']['credentials']['host']}")
    print(f"DB Port: {tortoise_config['connections']['mysql']['credentials']['port']}")
    print(f"DB Name: {tortoise_config['connections']['mysql']['credentials']['database']}")
    print()

    # 使用 aerich 进行迁移
    from aerich import Command

    command = Command(tortoise_config=tortoise_config)
    await command.init()

    # 1. 初始化数据库表（safe=True 只创建不存在的表）
    print("Initializing database tables (safe mode)...")
    try:
        await command.init_db(safe=True)
        print("  - Database tables initialized")
    except FileExistsError:
        print("  - Tables already exist, skipping")
    except Exception as e:
        print(f"  - Warning: {e}")

    # 2. 执行待定迁移
    print("Running pending migrations...")
    try:
        await command.upgrade(run_in_transaction=True)
        print("  - Migrations completed")
    except Exception as e:
        print(f"  - Migration result: {e}")

    print()
    print("=" * 50)
    print("Database migration completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_migration())
