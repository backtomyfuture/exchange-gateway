"""
Exchange 邮件服务相关 Schema 定义
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# =============================================================================
# 通用模型
# =============================================================================


class EmailAddress(BaseModel):
    """邮件地址"""

    email: EmailStr
    name: str | None = None


# =============================================================================
# 邮件发送相关
# =============================================================================


class EmailAttachment(BaseModel):
    """邮件附件"""

    filename: str = Field(..., description="文件名", max_length=255)
    content: str = Field(..., description="Base64编码的文件内容")
    content_type: str | None = Field(None, description="MIME类型")

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v):
        """验证附件大小不超过10MB（Base64编码后约13.3MB）"""
        max_size = 14 * 1024 * 1024  # 14MB for Base64 encoded 10MB file
        if len(v) > max_size:
            raise ValueError("附件大小超过限制（最大10MB）")
        return v


class EmailSendRequest(BaseModel):
    """发送邮件请求"""

    account_id: int = Field(..., description="发送账户ID")
    to: list[str] = Field(..., description="收件人邮箱列表")
    subject: str = Field(..., description="邮件主题")
    body: str = Field(..., description="邮件正文")
    body_type: str = Field("text", description="正文类型: text/html")
    cc: list[str] | None = Field(None, description="抄送列表")
    bcc: list[str] | None = Field(None, description="密送列表")
    attachments: list[EmailAttachment] | None = Field(None, description="附件列表")
    save_to_sent: bool = Field(True, description="是否保存到已发送")


class EmailDraftRequest(BaseModel):
    """创建草稿请求"""

    account_id: int = Field(..., description="账户ID")
    to: list[str] | None = Field(None, description="收件人邮箱列表")
    subject: str | None = Field(None, description="邮件主题")
    body: str | None = Field(None, description="邮件正文")
    body_type: str = Field("html", description="正文类型: text/html")
    cc: list[str] | None = Field(None, description="抄送列表")
    bcc: list[str] | None = Field(None, description="密送列表")
    attachments: list[EmailAttachment] | None = Field(None, description="附件列表")


class EmailReplyRequest(BaseModel):
    """回复邮件请求"""

    account_id: int = Field(..., description="账户ID")
    reference_item_id: str = Field(..., description="原邮件ID")
    folder: str = Field("INBOX", description="原邮件所在文件夹")
    to: list[str] | None = Field(None, description="收件人邮箱列表（不填则默认回复给发送者/所有人）")
    subject: str | None = Field(None, description="邮件主题（不填则自动添加 Re:）")
    body: str = Field(..., description="回复内容（仅用户新增内容，Exchange 自动拼接原文）")
    body_type: str = Field("html", description="正文类型: text/html")
    cc: list[str] | None = Field(None, description="抄送列表")
    bcc: list[str] | None = Field(None, description="密送列表")
    attachments: list[EmailAttachment] | None = Field(None, description="附件列表")
    reply_all: bool = Field(False, description="是否回复所有人")
    save_as_draft: bool = Field(False, description="是否仅保存为草稿（不发送）")


class EmailForwardRequest(BaseModel):
    """转发邮件请求"""

    account_id: int = Field(..., description="账户ID")
    reference_item_id: str = Field(..., description="原邮件ID")
    folder: str = Field("INBOX", description="原邮件所在文件夹")
    to: list[str] = Field(..., description="收件人邮箱列表")
    subject: str | None = Field(None, description="邮件主题（不填则自动添加 Fwd:）")
    body: str = Field("", description="转发附言（仅用户附言，Exchange 自动拼接原文）")
    body_type: str = Field("html", description="正文类型: text/html")
    cc: list[str] | None = Field(None, description="抄送列表")
    bcc: list[str] | None = Field(None, description="密送列表")
    attachments: list[EmailAttachment] | None = Field(None, description="附件列表")
    save_as_draft: bool = Field(False, description="是否仅保存为草稿（不发送）")


class EmailSendResponse(BaseModel):
    """发送邮件响应"""

    success: bool
    message: str
    log_id: int | None = None


# =============================================================================
# 邮件接收相关
# =============================================================================


class EmailListRequest(BaseModel):
    """获取邮件列表请求"""

    account_id: int = Field(..., description="账户ID")
    folder: str = Field("INBOX", description="文件夹名称")
    limit: int = Field(20, ge=1, le=100, description="获取数量")
    offset: int = Field(0, ge=0, description="偏移量")
    unread_only: bool = Field(False, description="仅未读邮件")


class EmailSyncRequest(BaseModel):
    """邮件同步请求"""

    account_id: int = Field(..., description="账户ID")
    folder: str = Field("INBOX", description="文件夹名称")
    sync_state: str | None = Field(None, description="同步状态")
    limit: int = Field(100, ge=1, le=500, description="获取数量")
    only_fields: list[str] | None = Field(None, description="仅返回指定字段")


class EmailItem(BaseModel):
    """邮件列表项"""

    id: str = Field(..., description="邮件ID")
    subject: str | None = None
    sender: str | None = None
    received_time: datetime | None = None
    is_read: bool = False
    has_attachments: bool = False


class EmailSyncItem(BaseModel):
    """邮件同步项"""

    change_type: str = Field(..., description="变更类型: create, update, delete")
    id: str = Field(..., description="邮件ID")
    item: EmailItem | None = None


class EmailListResponse(BaseModel):
    """邮件列表响应"""

    success: bool
    total: int
    items: list[EmailItem]


class EmailSyncResponse(BaseModel):
    """邮件同步响应"""

    success: bool
    sync_state: str
    items: list[EmailSyncItem]


class EmailDetailResponse(BaseModel):
    """邮件详情响应"""

    success: bool
    data: dict | None = None
    message: str | None = None


# =============================================================================
# 邮件搜索相关
# =============================================================================


class EmailSearchRequest(BaseModel):
    """搜索邮件请求"""

    account_id: int = Field(..., description="账户ID")
    query: str = Field(..., description="搜索关键词")
    folder: str = Field("INBOX", description="搜索文件夹")
    date_from: datetime | None = Field(None, description="开始日期")
    date_to: datetime | None = Field(None, description="结束日期")
    limit: int = Field(20, ge=1, le=100, description="返回数量")


class FolderItem(BaseModel):
    """文件夹信息 (Legacy)"""

    name: str = Field(..., description="文件夹名称")
    total_count: int = Field(0, description="总项目数")
    unread_count: int = Field(0, description="未读项目数")


class FolderDetailItem(BaseModel):
    """文件夹详细信息"""

    id: str = Field(..., description="文件夹ID")
    changekey: str = Field(..., description="ChangeKey")
    name: str = Field(..., description="文件夹名称")
    parent_id: str | None = Field(None, description="父文件夹ID")
    folder_class: str | None = Field(None, description="文件夹类别 (e.g. IPF.Note)")
    total_count: int = Field(0, description="总项目数")
    unread_count: int = Field(0, description="未读项目数")
    child_folder_count: int = Field(0, description="子文件夹数")


class FolderListResponse(BaseModel):
    """文件夹列表响应"""

    success: bool
    folders: list[FolderDetailItem]


# =============================================================================
# 账户管理相关
# =============================================================================


class AccountCreate(BaseModel):
    """创建邮箱账户"""

    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., description="登录用户名（不含域名）")
    password: str = Field(..., description="邮箱密码")
    display_name: str | None = Field(None, description="显示名称")
    server: str | None = Field(None, description="服务器地址（可选，使用默认）")
    domain: str | None = Field(None, description="域名（可选，使用默认）")
    remark: str | None = Field(None, description="备注")


class AccountUpdate(BaseModel):
    """更新邮箱账户"""

    id: int
    display_name: str | None = None
    password: str | None = Field(None, description="新密码（留空则不更新）")
    server: str | None = None
    domain: str | None = None
    is_active: bool | None = None
    remark: str | None = None


class AccountResponse(BaseModel):
    """邮箱账户响应"""

    id: int
    email: str
    username: str
    display_name: str | None
    server: str | None
    domain: str | None
    is_active: bool
    is_verified: bool
    last_verified_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime


class AccountTestResponse(BaseModel):
    """测试账户连接响应"""

    success: bool
    message: str


# =============================================================================
# API 密钥管理相关
# =============================================================================


class ApiKeyCreate(BaseModel):
    """创建API密钥"""

    name: str = Field(..., description="密钥名称")
    permissions: list[str] = Field(default=["send", "receive", "search"], description="权限列表")
    allowed_accounts: list[int] = Field(default=[], description="允许使用的账户ID（空表示全部）")
    ip_whitelist: list[str] = Field(default=[], description="IP白名单（空表示不限制）")
    rate_limit: int = Field(100, ge=1, le=10000, description="每分钟请求限制")
    expires_days: int | None = Field(None, description="过期天数（空表示使用默认）")
    remark: str | None = Field(None, description="备注")


class ApiKeyResponse(BaseModel):
    """API密钥响应（不含完整密钥）"""

    id: int
    name: str
    key_prefix: str
    permissions: list[str]
    allowed_accounts: list[int]
    ip_whitelist: list[str]
    rate_limit: int
    expires_at: datetime | None
    is_active: bool
    last_used_at: datetime | None
    usage_count: int
    remark: str | None
    created_at: datetime


class ApiKeyCreateResponse(BaseModel):
    """创建API密钥响应（包含完整密钥，仅显示一次）"""

    id: int
    name: str
    api_key: str = Field(..., description="完整API密钥（仅此一次显示）")
    key_prefix: str
    expires_at: datetime | None


# =============================================================================
# 使用统计相关
# =============================================================================


class UsageStatsRequest(BaseModel):
    """使用统计请求"""

    date_from: datetime | None = None
    date_to: datetime | None = None
    group_by: str = Field("day", description="分组方式: day/week/month")


class UsageStatsItem(BaseModel):
    """使用统计项"""

    period: str
    total_count: int
    success_count: int
    failed_count: int
    by_action: dict[str, int]


class UsageStatsResponse(BaseModel):
    """使用统计响应"""

    success: bool
    stats: list[UsageStatsItem]
    total: dict


# =============================================================================
# 邮件日志相关
# =============================================================================


class MailLogItem(BaseModel):
    """邮件日志项"""

    id: int
    api_key_id: int | None
    api_key_name: str | None
    account_id: int
    account_email: str | None
    action: str
    recipients: list[str] | None
    subject: str | None
    status: str
    error_message: str | None
    request_ip: str | None
    created_at: datetime


class MailLogListResponse(BaseModel):
    """邮件日志列表响应"""

    success: bool
    total: int
    items: list[MailLogItem]


# =============================================================================
# 邮件模板相关
# =============================================================================


class TemplateCreate(BaseModel):
    """创建邮件模板"""

    name: str = Field(..., description="模板名称")
    subject: str = Field(..., description="邮件主题")
    body: str = Field(..., description="邮件正文")
    body_type: str = Field("html", description="正文类型: text/html")
    category: str | None = Field(None, description="分类标签")
    variables: list[str] = Field(default=[], description="变量列表")
    remark: str | None = Field(None, description="备注")


class TemplateUpdate(BaseModel):
    """更新邮件模板"""

    id: int
    name: str | None = None
    subject: str | None = None
    body: str | None = None
    body_type: str | None = None
    category: str | None = None
    variables: list[str] | None = None
    is_active: bool | None = None
    remark: str | None = None


class TemplateResponse(BaseModel):
    """邮件模板响应"""

    id: int
    name: str
    subject: str
    body: str
    body_type: str
    category: str | None
    variables: list[str]
    is_active: bool
    remark: str | None
    created_at: datetime
    updated_at: datetime


class TemplatePreviewRequest(BaseModel):
    """模板预览请求"""

    template_id: int
    variables: dict[str, str] = Field(default={}, description="变量值字典")


class TemplateSendRequest(BaseModel):
    """使用模板发送邮件请求"""

    template_id: int | None = Field(None, description="模板ID（与template_name二选一）")
    template_name: str | None = Field(None, description="模板名称（与template_id二选一）")
    account_id: int = Field(..., description="发送账户ID")
    to: list[str] = Field(..., description="收件人邮箱列表")
    variables: dict[str, str] = Field(default={}, description="变量值字典")
    cc: list[str] | None = Field(None, description="抄送列表")
    bcc: list[str] | None = Field(None, description="密送列表")
    attachments: list[EmailAttachment] | None = Field(None, description="附件列表")

    @field_validator("template_name", mode="before")
    @classmethod
    def validate_template_identifier(cls, v, info):
        # 允许至少有一个模板标识符
        return v
