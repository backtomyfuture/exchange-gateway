"""
Webhook 订阅模型
"""
from tortoise import fields

from .base import BaseModel, TimestampMixin


class WebhookSubscription(BaseModel, TimestampMixin):
    """
    Webhook 订阅模型
    存储外部服务对邮件事件的订阅信息
    """
    # 订阅基本信息
    url = fields.CharField(max_length=500, description="回调地址", db_index=True)
    secret = fields.CharField(max_length=100, description="签名密钥 (HMAC SHA256)")
    
    # 关联账户
    account_id = fields.BigIntField(description="关联的 Exchange 账户ID", db_index=True)
    
    # 订阅配置
    events = fields.JSONField(default=list, description="订阅事件列表")
    # 可选: ["NewMail", "Created", "Deleted", "Modified"]
    folders = fields.JSONField(default=list, description="监听文件夹列表")
    # 例如: ["Inbox"]
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否启用", db_index=True)
    failure_count = fields.IntField(default=0, description="连续失败次数")
    last_failure_at = fields.DatetimeField(null=True, description="最后失败时间")
    last_success_at = fields.DatetimeField(null=True, description="最后成功时间")
    
    # 归属信息
    created_by = fields.BigIntField(description="创建者用户ID", db_index=True)
    
    # 备注
    remark = fields.CharField(max_length=500, null=True, description="备注")

    class Meta:
        table = "webhook_subscription"
