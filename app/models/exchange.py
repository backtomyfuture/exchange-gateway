"""
Exchange 邮件服务相关数据模型
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class ExchangeAccount(BaseModel, TimestampMixin):
    """
    邮箱账户模型
    存储Exchange邮箱账户信息，密码加密存储
    """
    # 账户基本信息
    email = fields.CharField(max_length=255, unique=True, description="邮箱地址", db_index=True)
    username = fields.CharField(max_length=100, description="登录用户名（不含域名）", db_index=True)
    encrypted_password = fields.TextField(description="加密后的密码")
    display_name = fields.CharField(max_length=100, null=True, description="显示名称")
    
    # 服务器配置（可覆盖全局配置）
    server = fields.CharField(max_length=255, null=True, description="Exchange服务器地址")
    domain = fields.CharField(max_length=100, null=True, description="域名")
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否启用", db_index=True)
    is_verified = fields.BooleanField(default=False, description="是否已验证连接", db_index=True)
    last_verified_at = fields.DatetimeField(null=True, description="最后验证时间")
    
    # 归属用户（管理后台用户）
    owner_id = fields.BigIntField(description="所属用户ID", db_index=True)
    
    # 备注
    remark = fields.CharField(max_length=500, null=True, description="备注")

    class Meta:
        table = "exchange_account"


class ExchangeApiKey(BaseModel, TimestampMixin):
    """
    API 密钥模型
    用于第三方系统调用邮件接口的认证
    """
    # 密钥信息
    name = fields.CharField(max_length=100, description="密钥名称", db_index=True)
    key_prefix = fields.CharField(max_length=8, description="密钥前缀（用于识别）", db_index=True)
    key_hash = fields.CharField(max_length=64, unique=True, description="密钥哈希值", db_index=True)
    
    # 权限控制
    permissions = fields.JSONField(default=list, description="权限列表")
    # 可选值: ["send", "receive", "search", "delete", "folders", "sync", "read", "reply", "forward", "contacts", "webhook"]
    
    # 关联账户（可关联多个）
    allowed_accounts = fields.JSONField(default=list, description="允许使用的账户ID列表")
    
    # 安全设置
    ip_whitelist = fields.JSONField(default=list, description="IP白名单")
    rate_limit = fields.IntField(default=100, description="每分钟请求限制")
    
    # 有效期
    expires_at = fields.DatetimeField(null=True, description="过期时间", db_index=True)
    is_active = fields.BooleanField(default=True, description="是否启用", db_index=True)
    
    # 使用统计
    last_used_at = fields.DatetimeField(null=True, description="最后使用时间")
    usage_count = fields.BigIntField(default=0, description="使用次数")
    
    # 归属用户
    owner_id = fields.BigIntField(description="所属用户ID", db_index=True)
    
    # 备注
    remark = fields.CharField(max_length=500, null=True, description="备注")

    class Meta:
        table = "exchange_api_key"


class ExchangeMailLog(BaseModel, TimestampMixin):
    """
    邮件操作日志模型
    记录所有邮件发送、接收等操作
    """
    # 关联信息
    api_key_id = fields.BigIntField(null=True, description="使用的API密钥ID", db_index=True)
    account_id = fields.BigIntField(description="使用的邮箱账户ID", db_index=True)
    
    # 操作类型
    action = fields.CharField(max_length=20, description="操作类型", db_index=True)
    # 可选值: send, receive, search, delete, move, list_folders, reply, forward
    
    # 邮件信息
    recipients = fields.JSONField(null=True, description="收件人列表")
    cc_recipients = fields.JSONField(null=True, description="抄送列表")
    bcc_recipients = fields.JSONField(null=True, description="密送列表")
    subject = fields.CharField(max_length=500, null=True, description="邮件主题")
    has_attachments = fields.BooleanField(default=False, description="是否有附件")
    
    # 执行结果
    status = fields.CharField(max_length=20, default="pending", description="状态", db_index=True)
    # 可选值: pending, success, failed
    error_message = fields.TextField(null=True, description="错误信息")
    
    # 请求信息
    request_ip = fields.CharField(max_length=50, null=True, description="请求IP")
    request_id = fields.CharField(max_length=50, null=True, description="请求ID", db_index=True)

    # 邮件内容持久化（用于ARQ重试/恢复）
    # 存储序列化的 EmailSendRequest，供进程重启后重新入队
    request_body = fields.JSONField(null=True, default=None, description="序列化的发送请求体，用于ARQ重试")

    class Meta:
        table = "exchange_mail_log"


class ExchangeEmailTemplate(BaseModel, TimestampMixin):
    """
    邮件模板模型
    存储预设的邮件模板，支持变量替换
    """
    # 模板基本信息
    name = fields.CharField(max_length=100, description="模板名称", db_index=True)
    subject = fields.CharField(max_length=500, description="邮件主题")
    body = fields.TextField(description="邮件正文")
    body_type = fields.CharField(max_length=10, default="html", description="正文类型: text/html")
    
    # 分类和变量
    category = fields.CharField(max_length=50, null=True, description="分类标签", db_index=True)
    variables = fields.JSONField(default=list, description="变量列表")
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否启用", db_index=True)
    
    # 归属用户
    owner_id = fields.BigIntField(description="所属用户ID", db_index=True)
    
    # 备注
    remark = fields.CharField(max_length=500, null=True, description="备注")

    class Meta:
        table = "exchange_email_template"


class ExchangeAuditLog(BaseModel, TimestampMixin):
    """
    管理操作审计日志模型
    记录账户管理、API密钥管理等敏感操作
    """
    # 操作者信息
    operator_id = fields.BigIntField(description="操作者用户ID", db_index=True)
    operator_name = fields.CharField(max_length=100, null=True, description="操作者用户名")
    
    # 操作类型
    action = fields.CharField(max_length=50, description="操作类型", db_index=True)
    # 可选值: 
    # 账户: create_account, update_account, delete_account, test_account
    # 密钥: create_api_key, revoke_api_key, delete_api_key
    # 模板: create_template, update_template, delete_template
    
    # 资源信息
    resource_type = fields.CharField(max_length=50, description="资源类型", db_index=True)
    # 可选值: account, api_key, template
    resource_id = fields.BigIntField(null=True, description="资源ID", db_index=True)
    resource_name = fields.CharField(max_length=255, null=True, description="资源名称/标识")
    
    # 操作详情
    details = fields.JSONField(null=True, description="操作详情（变更前后对比等）")
    
    # 请求信息
    request_ip = fields.CharField(max_length=50, null=True, description="请求IP")
    user_agent = fields.CharField(max_length=500, null=True, description="User-Agent")
    
    # 结果
    status = fields.CharField(max_length=20, default="success", description="操作状态")
    # 可选值: success, failed
    error_message = fields.TextField(null=True, description="错误信息")

    class Meta:
        table = "exchange_audit_log"
