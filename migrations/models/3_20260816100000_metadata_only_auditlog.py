from tortoise import BaseDBAsyncClient


async def _exists(db: BaseDBAsyncClient, query: str, values: list[str]) -> bool:
    _, rows = await db.execute_query(query, values)
    return bool(rows)


async def upgrade(db: BaseDBAsyncClient) -> str:
    column_exists = await _exists(
        db,
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        ["auditlog", "request_id"],
    )
    if not column_exists:
        await db.execute_script(
            """
            ALTER TABLE `auditlog`
                ADD COLUMN `request_id` VARCHAR(64) NULL COMMENT '请求ID' AFTER `response_time`;
            """
        )

    index_exists = await _exists(
        db,
        """
        SELECT 1
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        LIMIT 1
        """,
        ["auditlog", "idx_auditlog_request_id"],
    )
    if not index_exists:
        await db.execute_script(
            """
            CREATE INDEX `idx_auditlog_request_id`
                ON `auditlog` (`request_id`);
            """
        )

    # Aerich executes the returned script after this function. Keep it
    # non-empty because some drivers reject an empty SQL string.
    return "SELECT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP INDEX `idx_auditlog_request_id` ON `auditlog`;
ALTER TABLE `auditlog`
    DROP COLUMN `request_id`;
"""
