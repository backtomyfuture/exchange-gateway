"""
Migration: Add webhook menu and assign to role
Created: 2026-02-16
"""

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    # Insert or update "邮件服务" catalog menu
    await db.execute_query("""
        INSERT INTO `menu` (`name`, `remark`, `menu_type`, `icon`, `path`, `order`, `parent_id`, `is_hidden`, `component`, `keepalive`, `redirect`, `created_at`, `updated_at`)
        VALUES ('邮件服务', NULL, 'catalog', 'ph:envelope-simple-open-bold', '/exchange', 10, 0, 0, 'Layout', 1, NULL, NOW(), NOW())
        ON DUPLICATE KEY UPDATE `name` = '邮件服务', `menu_type` = 'catalog', `icon` = 'ph:envelope-simple-open-bold', `path` = '/exchange', `order` = 10, `component` = 'Layout'
    """)

    # Get the parent menu ID
    _, result = await db.execute_query(
        "SELECT `id` FROM `menu` WHERE `name` = '邮件服务' AND `menu_type` = 'catalog' LIMIT 1"
    )
    parent_id = None
    if result:
        row = result[0]
        parent_id = row['id'] if isinstance(row, dict) else row[0]

    if parent_id:
        # Insert or update "Webhook 订阅" menu
        await db.execute_query(
            """
            INSERT INTO `menu` (`name`, `remark`, `menu_type`, `icon`, `path`, `order`, `parent_id`, `is_hidden`, `component`, `keepalive`, `redirect`, `created_at`, `updated_at`)
            VALUES ('Webhook 订阅', NULL, 'menu', 'connection', '/exchange/webhooks', 99, {}, 0, 'exchange/webhooks/index', 1, NULL, NOW(), NOW())
            ON DUPLICATE KEY UPDATE `path` = '/exchange/webhooks', `component` = 'exchange/webhooks/index', `icon` = 'connection', `parent_id` = {}
        """.format(parent_id, parent_id)
        )

        # Get webhook menu ID
        _, result = await db.execute_query(
            "SELECT `id` FROM `menu` WHERE `name` = 'Webhook 订阅' AND `parent_id` = {} LIMIT 1".format(parent_id)
        )
        webhook_menu_id = None
        if result:
            row = result[0]
            webhook_menu_id = row['id'] if isinstance(row, dict) else row[0]

        if webhook_menu_id:
            # Get role ID for "邮箱用户"
            _, result = await db.execute_query("SELECT `id` FROM `role` WHERE `name` = '邮箱用户' LIMIT 1")
            role_id = None
            if result:
                row = result[0]
                role_id = row['id'] if isinstance(row, dict) else row[0]

            if role_id:
                # Insert into role_menu (many-to-many)
                await db.execute_query(
                    """
                    INSERT IGNORE INTO `role_menu` (`role_id`, `menu_id`) VALUES ({}, {})
                """.format(role_id, webhook_menu_id)
                )

    # Cleanup: Remove old "Exchange 管理" parent if empty
    _, result = await db.execute_query(
        "SELECT `id` FROM `menu` WHERE `name` = 'Exchange 管理' AND `menu_type` = 'catalog' LIMIT 1"
    )
    old_parent_id = None
    if result:
        row = result[0]
        old_parent_id = row['id'] if isinstance(row, dict) else row[0]

    if old_parent_id:
        # Check if has children
        _, result = await db.execute_query("SELECT COUNT(*) FROM `menu` WHERE `parent_id` = {}".format(old_parent_id))
        count = 0
        if result:
            row = result[0]
            count = list(row.values())[0] if isinstance(row, dict) else row[0]

        if count == 0:
            # Delete old parent
            await db.execute_query("DELETE FROM `menu` WHERE `id` = {}".format(old_parent_id))
        else:
            # Delete old webhook under this parent
            await db.execute_query(
                "DELETE FROM `menu` WHERE `name` = 'Webhook 订阅' AND `parent_id` = {}".format(old_parent_id)
            )

    return "SELECT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    # Remove webhook menu
    await db.execute_query("DELETE FROM `menu` WHERE `name` = 'Webhook 订阅'")
    # Remove parent if empty
    await db.execute_query("DELETE FROM `menu` WHERE `name` = '邮件服务' AND `parent_id` = 0")
    return None
