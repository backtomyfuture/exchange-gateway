from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `webhook_subscription` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `url` VARCHAR(500) NOT NULL  COMMENT '回调地址',
    `secret` VARCHAR(100) NOT NULL  COMMENT '签名密钥 (HMAC SHA256)',
    `account_id` BIGINT NOT NULL  COMMENT '关联的 Exchange 账户ID',
    `events` JSON NOT NULL  COMMENT '订阅事件列表',
    `folders` JSON NOT NULL  COMMENT '监听文件夹列表',
    `is_active` BOOL NOT NULL  COMMENT '是否启用' DEFAULT 1,
    `failure_count` INT NOT NULL  COMMENT '连续失败次数' DEFAULT 0,
    `last_failure_at` DATETIME(6)   COMMENT '最后失败时间',
    `last_success_at` DATETIME(6)   COMMENT '最后成功时间',
    `created_by` BIGINT NOT NULL  COMMENT '创建者用户ID',
    `remark` VARCHAR(500)   COMMENT '备注',
    KEY `idx_webhook_sub_created_d8201c` (`created_at`),
    KEY `idx_webhook_sub_updated_ef82d8` (`updated_at`),
    KEY `idx_webhook_sub_url_1853dd` (`url`),
    KEY `idx_webhook_sub_account_5455a7` (`account_id`),
    KEY `idx_webhook_sub_is_acti_9b421c` (`is_active`),
    KEY `idx_webhook_sub_created_bd93da` (`created_by`)
) CHARACTER SET utf8mb4 COMMENT='Webhook 订阅模型';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `webhook_subscription`;"""
