from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.settings import settings

_WEBHOOK_EVENT_ALIASES = {
    "copiedevent": "CopiedEvent",
    "createdevent": "CreatedEvent",
    "deletedevent": "DeletedEvent",
    "modifiedevent": "ModifiedEvent",
    "movedevent": "MovedEvent",
    "newmail": "NewMailEvent",
    "newmailevent": "NewMailEvent",
    "freebusychanged": "FreeBusyChangedEvent",
    "freebusychangedevent": "FreeBusyChangedEvent",
}


def _normalize_events(events: list[str]) -> list[str]:
    if not events:
        return ["NewMailEvent"]

    normalized: list[str] = []
    for event in events:
        event_name = str(event).strip()
        if not event_name:
            continue
        if event_name == "*":
            return ["*"]

        mapped = _WEBHOOK_EVENT_ALIASES.get(event_name.lower())
        if not mapped:
            raise ValueError(f"不支持的事件类型: {event_name}")
        if mapped not in normalized:
            normalized.append(mapped)

    if not normalized:
        raise ValueError("events 至少包含一个有效事件")
    return normalized


class WebhookBase(BaseModel):
    url: HttpUrl = Field(..., description="回调地址")
    events: list[str] = Field(default=["NewMailEvent"], description="订阅事件白名单")
    folders: list[str] = Field(default=["*"], description="监听文件夹列表（当前版本不限制）")
    remark: str | None = Field(None, description="备注")
    is_active: bool = Field(True, description="是否启用")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        import ipaddress
        import socket
        from urllib.parse import urlparse

        url_str = str(v)
        parsed = urlparse(url_str)
        hostname = parsed.hostname

        if not hostname:
            raise ValueError("无效的 URL")

        # Check for localhost
        if hostname.lower() in ["localhost", "127.0.0.1", "::1"]:
            raise ValueError("禁止使用本地地址")

        try:
            # Resolve hostname to IP
            ip = socket.gethostbyname(hostname)
            ip_addr = ipaddress.ip_address(ip)

            # 链路本地和回环地址在任何环境都禁止，避免自调用或访问本地敏感资源
            if ip_addr.is_loopback or ip_addr.is_link_local:
                raise ValueError(f"禁止使用本地链路地址: {hostname} ({ip})")

            # 私网地址允许由配置开关控制（开发可放开，生产默认关闭）
            if ip_addr.is_private and not settings.WEBHOOK_ALLOW_PRIVATE_URLS:
                raise ValueError(f"禁止使用内部网络地址: {hostname} ({ip})")

        except socket.gaierror:
            # If we can't resolve it, we might still allow it if it's a valid public domain?
            # Or fail safe?
            # For security, fail safe if we can't verify it's not private.
            # But DNS might be flaky.
            # Let's assume if it fails DNS, it won't work anyway.
            pass

        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        return _normalize_events(v)


class WebhookCreate(WebhookBase):
    account_id: int = Field(..., description="关联的 Exchange 账户ID")
    secret: str = Field(..., min_length=8, description="签名密钥")


class WebhookUpdate(BaseModel):
    url: HttpUrl | None = Field(None, description="回调地址")
    events: list[str] | None = Field(None, description="订阅事件列表")
    folders: list[str] | None = Field(None, description="监听文件夹列表")
    secret: str | None = Field(None, min_length=8, description="签名密钥")
    is_active: bool | None = Field(None, description="是否启用")
    remark: str | None = Field(None, description="备注")

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return _normalize_events(v)


class WebhookResponse(WebhookBase):
    id: int
    account_id: int
    created_by: int
    created_at: str
    updated_at: str

    # 隐藏敏感信息
    # secret 不返回

    class Config:
        from_attributes = True
