from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `webhook_delivery` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `event_type` VARCHAR(100) NOT NULL COMMENT '事件类型',
            `payload` JSON NOT NULL COMMENT '事件载荷',
            `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态',
            `attempt_count` INT NOT NULL DEFAULT 0 COMMENT '尝试次数',
            `last_error` LONGTEXT NULL COMMENT '最后错误信息',
            `next_retry_at` DATETIME(6) NULL COMMENT '下次重试时间',
            `subscription_id` BIGINT NOT NULL,
            CONSTRAINT `fk_webhook_d_webhook_s_subscription` FOREIGN KEY (`subscription_id`)
                REFERENCES `webhook_subscription` (`id`) ON DELETE CASCADE,
            KEY `idx_webhook_delivery_status` (`status`)
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `webhook_delivery`;"""
