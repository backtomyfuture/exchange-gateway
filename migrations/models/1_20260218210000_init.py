from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS `api` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `path` VARCHAR(100) NOT NULL COMMENT 'API路径',
    `method` VARCHAR(6) NOT NULL COMMENT '请求方法',
    `summary` VARCHAR(500) NOT NULL COMMENT '请求简介',
    `tags` VARCHAR(100) NOT NULL COMMENT 'API标签',
    KEY `idx_api_path_9ed611` (`path`),
    KEY `idx_api_method_a46dfb` (`method`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `auditlog` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT '用户ID',
    `username` VARCHAR(64) NOT NULL COMMENT '用户名称' DEFAULT '',
    `module` VARCHAR(64) NOT NULL COMMENT '功能模块' DEFAULT '',
    `summary` VARCHAR(128) NOT NULL COMMENT '请求描述' DEFAULT '',
    `method` VARCHAR(10) NOT NULL COMMENT '请求方法' DEFAULT '',
    `path` VARCHAR(255) NOT NULL COMMENT '请求路径' DEFAULT '',
    `status` INT NOT NULL COMMENT '状态码' DEFAULT -1,
    `response_time` INT NOT NULL COMMENT '响应时间(单位ms)' DEFAULT 0,
    `request_args` JSON COMMENT '请求参数',
    `response_body` JSON COMMENT '返回数据',
    KEY `idx_auditlog_user_id_4b93fa` (`user_id`),
    KEY `idx_auditlog_status_2a72d2` (`status`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `dept` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL UNIQUE COMMENT '部门名称',
    `desc` VARCHAR(500) COMMENT '备注',
    `is_deleted` BOOL NOT NULL COMMENT '软删除标记' DEFAULT 0,
    `order` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `parent_id` INT NOT NULL COMMENT '父部门ID' DEFAULT 0,
    UNIQUE KEY `uid_dept_parent__b9d39c` (`parent_id`, `name`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `deptclosure` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `ancestor` INT NOT NULL COMMENT '父代',
    `descendant` INT NOT NULL COMMENT '子代',
    `level` INT NOT NULL COMMENT '深度' DEFAULT 0,
    KEY `idx_deptclosure_ancesto_fbc4ce` (`ancestor`),
    KEY `idx_deptclosure_descend_2ae8b1` (`descendant`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `exchange_account` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `email` VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱地址',
    `username` VARCHAR(100) NOT NULL COMMENT '登录用户名（不含域名）',
    `encrypted_password` LONGTEXT NOT NULL COMMENT '加密后的密码',
    `display_name` VARCHAR(100) COMMENT '显示名称',
    `server` VARCHAR(255) COMMENT 'Exchange服务器地址',
    `domain` VARCHAR(100) COMMENT '域名',
    `is_active` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `is_verified` BOOL NOT NULL COMMENT '是否已验证连接' DEFAULT 0,
    `last_verified_at` DATETIME(6) COMMENT '最后验证时间',
    `owner_id` BIGINT NOT NULL COMMENT '所属用户ID',
    `remark` VARCHAR(500) COMMENT '备注',
    KEY `idx_exchange_ac_email_9340d8` (`email`),
    KEY `idx_exchange_ac_owner_i_73eac2` (`owner_id`)
) CHARACTER SET utf8mb4 COMMENT='邮箱账户模型';

CREATE TABLE IF NOT EXISTS `exchange_api_key` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(100) NOT NULL COMMENT '密钥名称',
    `key_prefix` VARCHAR(8) NOT NULL COMMENT '密钥前缀（用于识别）',
    `key_hash` VARCHAR(64) NOT NULL UNIQUE COMMENT '密钥哈希值',
    `permissions` JSON NOT NULL COMMENT '权限列表',
    `allowed_accounts` JSON NOT NULL COMMENT '允许使用的账户ID列表',
    `ip_whitelist` JSON NOT NULL COMMENT 'IP白名单',
    `rate_limit` INT NOT NULL COMMENT '每分钟请求限制' DEFAULT 100,
    `expires_at` DATETIME(6) COMMENT '过期时间',
    `is_active` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `last_used_at` DATETIME(6) COMMENT '最后使用时间',
    `usage_count` BIGINT NOT NULL COMMENT '使用次数' DEFAULT 0,
    `owner_id` BIGINT NOT NULL COMMENT '所属用户ID',
    `remark` VARCHAR(500) COMMENT '备注',
    KEY `idx_exchange_ap_key_has_48bbaa` (`key_hash`),
    KEY `idx_exchange_ap_owner_i_3a4993` (`owner_id`)
) CHARACTER SET utf8mb4 COMMENT='API 密钥模型';

CREATE TABLE IF NOT EXISTS `exchange_audit_log` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `operator_id` BIGINT NOT NULL COMMENT '操作者用户ID',
    `operator_name` VARCHAR(100) COMMENT '操作者用户名',
    `action` VARCHAR(50) NOT NULL COMMENT '操作类型',
    `resource_type` VARCHAR(50) NOT NULL COMMENT '资源类型',
    `resource_id` BIGINT COMMENT '资源ID',
    `resource_name` VARCHAR(255) COMMENT '资源名称/标识',
    `details` JSON COMMENT '操作详情（变更前后对比等）',
    `request_ip` VARCHAR(50) COMMENT '请求IP',
    `user_agent` VARCHAR(500) COMMENT 'User-Agent',
    `status` VARCHAR(20) NOT NULL COMMENT '操作状态' DEFAULT 'success',
    `error_message` LONGTEXT COMMENT '错误信息',
    KEY `idx_exchange_au_operato_1665b5` (`operator_id`),
    KEY `idx_exchange_au_resourc_961c59` (`resource_id`)
) CHARACTER SET utf8mb4 COMMENT='管理操作审计日志模型';

CREATE TABLE IF NOT EXISTS `exchange_email_template` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(100) NOT NULL COMMENT '模板名称',
    `subject` VARCHAR(500) NOT NULL COMMENT '邮件主题',
    `body` LONGTEXT NOT NULL COMMENT '邮件正文',
    `body_type` VARCHAR(10) NOT NULL COMMENT '正文类型: text/html' DEFAULT 'html',
    `category` VARCHAR(50) COMMENT '分类标签',
    `variables` JSON NOT NULL COMMENT '变量列表',
    `is_active` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `owner_id` BIGINT NOT NULL COMMENT '所属用户ID',
    `remark` VARCHAR(500) COMMENT '备注',
    KEY `idx_exchange_em_name_4b8741` (`name`),
    KEY `idx_exchange_em_owner_i_cccc24` (`owner_id`)
) CHARACTER SET utf8mb4 COMMENT='邮件模板模型';

CREATE TABLE IF NOT EXISTS `exchange_mail_log` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `api_key_id` BIGINT COMMENT '使用的API密钥ID',
    `account_id` BIGINT NOT NULL COMMENT '使用的邮箱账户ID',
    `action` VARCHAR(20) NOT NULL COMMENT '操作类型',
    `recipients` JSON COMMENT '收件人列表',
    `cc_recipients` JSON COMMENT '抄送列表',
    `bcc_recipients` JSON COMMENT '密送列表',
    `subject` VARCHAR(500) COMMENT '邮件主题',
    `has_attachments` BOOL NOT NULL COMMENT '是否有附件' DEFAULT 0,
    `status` VARCHAR(20) NOT NULL COMMENT '状态' DEFAULT 'pending',
    `error_message` LONGTEXT COMMENT '错误信息',
    `request_ip` VARCHAR(50) COMMENT '请求IP',
    `request_id` VARCHAR(50) COMMENT '请求ID',
    `request_body` JSON NULL COMMENT '序列化的发送请求体，用于ARQ重试',
    KEY `idx_exchange_ma_account_5376b5` (`account_id`),
    KEY `idx_exchange_ma_status_db58da` (`status`),
    KEY `idx_exchange_ma_request_333c59` (`request_id`)
) CHARACTER SET utf8mb4 COMMENT='邮件操作日志模型';



CREATE TABLE IF NOT EXISTS `menu` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '菜单名称',
    `remark` JSON COMMENT '保留字段',
    `menu_type` VARCHAR(10) COMMENT '菜单类型',
    `icon` VARCHAR(100) COMMENT '菜单图标',
    `path` VARCHAR(100) NOT NULL COMMENT '菜单路径',
    `order` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `parent_id` INT NOT NULL COMMENT '父菜单ID' DEFAULT 0,
    `is_hidden` BOOL NOT NULL COMMENT '是否隐藏' DEFAULT 0,
    `component` VARCHAR(100) NOT NULL COMMENT '组件',
    `keepalive` BOOL NOT NULL COMMENT '存活' DEFAULT 1,
    `redirect` VARCHAR(100) COMMENT '重定向',
    UNIQUE KEY `uid_menu_parent__bebd16` (`parent_id`, `name`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `role` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL UNIQUE COMMENT '角色名称',
    `desc` VARCHAR(500) COMMENT '角色描述',
    KEY `idx_role_name_e5618b` (`name`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `username` VARCHAR(20) NOT NULL UNIQUE COMMENT '用户名称',
    `alias` VARCHAR(30) COMMENT '姓名',
    `email` VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱',
    `phone` VARCHAR(20) COMMENT '电话',
    `password` VARCHAR(128) COMMENT '密码',
    `is_active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 1,
    `is_superuser` BOOL NOT NULL COMMENT '是否为超级管理员' DEFAULT 0,
    `last_login` DATETIME(6) COMMENT '最后登录时间',
    `dept_id` INT COMMENT '部门ID',
    KEY `idx_user_usernam_9987ab` (`username`),
    KEY `idx_user_email_1b4f1c` (`email`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `webhook_subscription` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `url` VARCHAR(500) NOT NULL COMMENT '回调地址',
    `secret` VARCHAR(100) NOT NULL COMMENT '签名密钥 (HMAC SHA256)',
    `account_id` BIGINT NOT NULL COMMENT '关联的 Exchange 账户ID',
    `events` JSON NOT NULL COMMENT '订阅事件列表',
    `folders` JSON NOT NULL COMMENT '监听文件夹列表',
    `is_active` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `failure_count` INT NOT NULL COMMENT '连续失败次数' DEFAULT 0,
    `last_failure_at` DATETIME(6) COMMENT '最后失败时间',
    `last_success_at` DATETIME(6) COMMENT '最后成功时间',
    `created_by` BIGINT NOT NULL COMMENT '创建者用户ID',
    `remark` VARCHAR(500) COMMENT '备注',
    KEY `idx_webhook_sub_url_1853dd` (`url`),
    KEY `idx_webhook_sub_is_acti_9b421c` (`is_active`)
) CHARACTER SET utf8mb4 COMMENT='Webhook 订阅模型';

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
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `role_menu` (
    `role_id` BIGINT NOT NULL,
    `menu_id` BIGINT NOT NULL,
    FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`menu_id`) REFERENCES `menu` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_role_menu_role_id_90801c` (`role_id`, `menu_id`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `role_api` (
    `role_id` BIGINT NOT NULL,
    `api_id` BIGINT NOT NULL,
    FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`api_id`) REFERENCES `api` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_role_api_role_id_ba4286` (`role_id`, `api_id`)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `user_role` (
    `user_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_user_role_user_id_d0bad3` (`user_id`, `role_id`)
) CHARACTER SET utf8mb4;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return ""
