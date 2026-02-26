# Exchange Gateway 开源改进实施计划

> **基准项目**: `exchange-gateway-old`（94 条干净 commit）
> **改进来源**: `exchange-feishu-extension`（选择性移植）
> **目标**: 打造符合业界最佳实践的开源项目

---

## 目录

1. [改进 #1：Redis 分布式迁移锁](#改进-1redis-分布式迁移锁)
2. [改进 #2：审计日志敏感数据脱敏](#改进-2审计日志敏感数据脱敏)
3. [改进 #3：审计日志 structlog 集成](#改进-3审计日志-structlog-集成)
4. [改进 #4：中间件用户识别优化](#改进-4中间件用户识别优化)
5. [改进 #5：异常体系扩展与规范化](#改进-5异常体系扩展与规范化)
6. [改进 #6：菜单初始化幂等化](#改进-6菜单初始化幂等化)
7. [改进 #7：Docker Compose 安全加固](#改进-7docker-compose-安全加固)
8. [改进 #8：EWS 异步辅助工具](#改进-8ews-异步辅助工具)
9. [改进 #9：Redis 分布式速率限制器](#改进-9redis-分布式速率限制器)
10. [改进 #10：API Key 认证模块优化](#改进-10api-key-认证模块优化)
11. [改进 #11：依赖注入与权限模块优化](#改进-11依赖注入与权限模块优化)
12. [环境配置简化](#环境配置简化)
13. [开源标准化](#开源标准化)
14. [测试用例要求](#测试用例要求)

---

## 改进 #1：Redis 分布式迁移锁

### 现状问题

**文件**: `app/core/init_app.py` → `init_db()` 函数（第 271-308 行）

当前 `init_db()` 在多 Worker 启动时使用字符串匹配检测并发冲突：

```python
# 当前代码（有问题）
if "Duplicate key" in str(e) or "already exists" in str(e):
    logger.info(f"Database migration already processed: {e}")
```

**问题**:
- 字符串匹配不可靠，不同数据库驱动的错误消息格式不同
- MySQL 与 PostgreSQL 的错误消息不一致
- 无法区分"迁移已完成"和"迁移真的失败了"

### 改进方案

#### 步骤 1：新建 `app/utils/migration_lock.py`

从 `exchange-feishu-extension` 完整复制此文件：

```python
"""Redis 分布式迁移锁。

确保多 worker 启动时只有一个 worker 执行 Aerich 迁移，
其他 worker 等待完成后直接跳过。
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class MigrationLock:
    """基于 Redis SET NX 的数据库迁移分布式锁。"""

    def __init__(self, redis_client, lock_key: str = "exchange-gw:migration-lock", ttl: int = 120):
        self._redis = redis_client
        self._key = lock_key
        self._ttl = ttl
        self._lock_value = f"worker-{time.monotonic_ns()}"

    async def acquire(self) -> bool:
        """尝试获取锁。返回 True 表示获取成功，False 表示已被其他 worker 持有。"""
        result = await self._redis.set(self._key, self._lock_value, ex=self._ttl, nx=True)
        if result:
            logger.info("迁移锁已获取")
            return True
        logger.info("迁移锁被其他 worker 持有，等待中")
        return False

    async def release(self) -> None:
        """释放锁。"""
        await self._redis.delete(self._key)
        logger.info("迁移锁已释放")

    async def wait_for_completion(self, poll_interval: float = 1.0, max_wait: float = 120.0) -> None:
        """等待直到锁被释放（其他 worker 完成迁移）。"""
        start = time.monotonic()
        while time.monotonic() - start < max_wait:
            val = await self._redis.get(self._key)
            if val is None:
                logger.info("其他 worker 已完成迁移")
                return
            await asyncio.sleep(poll_interval)
        logger.warning("等待迁移锁超时 %.1fs", max_wait)
```

#### 步骤 2：重写 `app/core/init_app.py` 中的 `init_db()` 函数

**删除**: 原第 271-308 行整个 `init_db()` 函数
**替换为**:

```python
async def _run_migrations():
    """执行 Aerich 迁移并同步 schema。"""
    try:
        from aerich import Command

        command = Command(tortoise_config=settings.TORTOISE_ORM, app="models")
        await command.init()
        await command.upgrade()
        await Tortoise.generate_schemas(safe=True)
        logger.info("数据库迁移已成功应用")
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        try:
            await Tortoise.generate_schemas(safe=True)
            logger.info("Schema 同步完成（safe 模式）")
        except Exception as se:
            logger.critical(f"数据库初始化失败: {se}")
            raise


async def init_db():
    """
    初始化数据库表
    使用 Redis 分布式锁确保只有一个 worker 执行迁移
    """
    import os

    auto_migrate = os.getenv("AUTO_MIGRATE", "true").lower() in ("true", "1", "yes")
    await Tortoise.init(config=settings.TORTOISE_ORM)

    if not auto_migrate:
        logger.info("AUTO_MIGRATE=false，跳过启动迁移")
        return

    # 尝试通过 Redis 分布式锁协调多 worker 迁移
    try:
        import redis.asyncio as aioredis

        from app.utils.migration_lock import MigrationLock

        redis_client = aioredis.from_url(settings.REDIS_URL)
        lock = MigrationLock(redis_client)

        if await lock.acquire():
            try:
                await _run_migrations()
            finally:
                await lock.release()
        else:
            # 另一个 worker 正在迁移，等待完成后跳过
            await lock.wait_for_completion()

        await redis_client.aclose()
    except Exception as e:
        # Redis 不可用时回退到直接迁移（单 worker 场景）
        logger.warning(f"Redis 锁不可用，直接执行迁移: {e}")
        await _run_migrations()
```

**同时需要修改**: `init_app.py` 头部 import，**删除** 第 1 行：

```diff
-from aerich import Command
```

因为 `Command` 现在只在 `_run_migrations()` 内部导入（延迟导入，避免启动时必须安装 aerich）。

---

## 改进 #2：审计日志敏感数据脱敏

### 现状问题

**文件**: `app/core/middlewares.py` → `get_request_args()` 方法（第 80-105 行）

当前审计日志会将请求体中的敏感字段（password、token、API Key 等）**明文记录**到数据库审计日志中。

### 改进方案

#### 在 `app/core/middlewares.py` 中新增脱敏函数

在 `class HttpAuditLogMiddleware` 定义之前（约第 72 行前），新增：

```python
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "key",
        "api_key",
        "x_api_key",
        "encrypted_password",
        "secret_key",
        "encryption_key",
        "authorization",
        "credential",
        "credentials",
    }
)


def _mask_sensitive(data: dict) -> dict:
    """递归脱敏字典中的敏感字段。"""
    if not isinstance(data, dict):
        return data
    masked = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            masked[k] = "***"
        elif isinstance(v, dict):
            masked[k] = _mask_sensitive(v)
        elif isinstance(v, list):
            masked[k] = [_mask_sensitive(i) if isinstance(i, dict) else i for i in v]
        else:
            masked[k] = v
    return masked
```

#### 修改 `get_request_args()` 返回值

**文件**: `app/core/middlewares.py` 第 105 行

```diff
-        return args
+        return _mask_sensitive(args)
```

---

## 改进 #3：审计日志 structlog 集成

### 现状问题

**文件**: `app/core/middlewares.py` 第 203-204 行

审计日志写入失败时使用 `print()` 输出：

```python
print(f"FAILED_TO_LOG: {str(e)}")
```

**问题**:
- `print()` 无法被日志采集系统捕获
- 不包含时间戳、日志级别等元信息

### 改进方案

#### 步骤 1：添加 import

在 `app/core/middlewares.py` 的 import 区域（约第 1-18 行），添加：

```python
import structlog
```

#### 步骤 2：添加模块级 logger

在 import 之后、class 定义之前，添加：

```python
_audit_logger = structlog.get_logger("audit")
```

#### 步骤 3：替换 print 语句

**文件**: `app/core/middlewares.py` 第 200-204 行

```diff
             try:
                 await AuditLog.create(**data)
             except Exception as e:
-                # 即使审计日志写入失败，也不应该影响正常业务流程
-                print(f"FAILED_TO_LOG: {str(e)}")
+                _audit_logger.warning("Failed to write audit log", error=str(e))
```

---

## 改进 #4：中间件用户识别优化

### 现状问题

**文件**: `app/core/middlewares.py` → `get_request_log()` 方法（第 152-184 行）

当前中间件在每个请求中 **重新解析 token** 来获取用户信息：

```python
token = request.headers.get("token")
user_obj = None
if token:
    user_obj: User = await AuthControl.is_authed(token)
```

**问题**:
- 重复的 token 解析逻辑（`AuthControl.is_authed` 已在依赖注入中执行过）
- `AuthControl.is_authed` 的签名已不再接受单独的 token 字符串参数
- 额外的 DB 查询，增加延迟

### 改进方案

**文件**: `app/core/middlewares.py` 第 172-184 行

**删除 import**（第 15 行）：
```diff
-from app.core.dependency import AuthControl
```

**替换** `get_request_log()` 中的用户获取逻辑：

```diff
         # 获取用户信息
-        try:
-            token = request.headers.get("token")
-            user_obj = None
-            if token:
-                user_obj: User = await AuthControl.is_authed(token)
-            data["user_id"] = user_obj.id if user_obj else 0
-            data["username"] = user_obj.username if user_obj else ""
-        except Exception:
-            data["user_id"] = 0
-            data["username"] = ""
+        # 从 request.state 获取已认证的用户信息，避免重复解析 token
+        user_id = 0
+        username = ""
+        try:
+            from app.core.ctx import CTX_USER_ID
+
+            user_id = CTX_USER_ID.get(0)
+            if user_id:
+                user_obj = await User.filter(id=user_id).first()
+                if user_obj:
+                    username = user_obj.username
+        except Exception:
+            pass
+        data["user_id"] = user_id
+        data["username"] = username
```

---

## 改进 #5：异常体系扩展与规范化

### 现状问题

**文件**: `app/core/exceptions.py`

1. **泄露内部错误详情**（安全风险）：

```python
# 第 15-19 行：泄露了 exc 异常详情和 query_params
async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        code=404,
        msg=f"Object has not found, exc: {exc}, query_params: {req.query_params}",
    )

# 第 23-28 行：泄露了 IntegrityError 详情
async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        code=500,
        msg=f"IntegrityError，{exc}",
    )

# 第 36-38 行：泄露了 RequestValidationError 详情
async def RequestValidationHandle(_: Request, exc: RequestValidationError) -> JSONResponse:
    content = dict(code=422, msg=f"RequestValidationError, {exc}")

# 第 41-43 行：泄露了 ResponseValidationError 详情
async def ResponseValidationHandle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    content = dict(code=500, msg=f"ResponseValidationError, {exc}")
```

2. **函数命名不符合 PEP 8**：使用大驼峰 `DoesNotExistHandle` 而非蛇形 `does_not_exist_handle`
3. **缺少 3 个领域异常类**：`AttachmentTooLargeError`、`WebhookDeliveryError`、`EmailNotFoundError`

### 改进方案

**完整替换** `app/core/exceptions.py`:

```python
from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError


class SettingNotFoundError(Exception):
    pass


SettingNotFound = SettingNotFoundError


async def does_not_exist_handle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        code=404,
        msg="请求的资源不存在",
    )
    return JSONResponse(content=content, status_code=404)


DoesNotExistHandle = does_not_exist_handle


async def integrity_handle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        code=500,
        msg="数据完整性错误，请检查是否存在重复或关联数据冲突",
    )
    return JSONResponse(content=content, status_code=500)


IntegrityHandle = integrity_handle


async def http_exc_handle(_: Request, exc: HTTPException) -> JSONResponse:
    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


HttpExcHandle = http_exc_handle


async def request_validation_handle(_: Request, exc: RequestValidationError) -> JSONResponse:
    content = dict(code=422, msg="请求参数验证失败", data=exc.errors())
    return JSONResponse(content=content, status_code=422)


RequestValidationHandle = request_validation_handle


async def response_validation_handle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    content = dict(code=500, msg="服务端响应数据异常")
    return JSONResponse(content=content, status_code=500)


ResponseValidationHandle = response_validation_handle


# =============================================================================
# Domain Exception Hierarchy
# =============================================================================


class EWSGatewayError(Exception):
    """Base class for all exchange-gateway domain exceptions."""

    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


EWSGatewayException = EWSGatewayError


class AccountNotFoundError(EWSGatewayError):
    error_code = "ACCOUNT_NOT_FOUND"
    http_status = 404


class AccountDisabledError(EWSGatewayError):
    error_code = "ACCOUNT_DISABLED"
    http_status = 403


class InvalidCredentialsError(EWSGatewayError):
    error_code = "INVALID_CREDENTIALS"
    http_status = 401


class ExchangeConnectionError(EWSGatewayError):
    error_code = "EXCHANGE_CONNECTION_ERROR"
    http_status = 503


class ExchangeTimeoutError(EWSGatewayError):
    error_code = "EXCHANGE_TIMEOUT"
    http_status = 504


class AttachmentTooLargeError(EWSGatewayError):
    error_code = "ATTACHMENT_TOO_LARGE"
    http_status = 413


class ExchangeAuthError(EWSGatewayError):
    error_code = "EXCHANGE_AUTH_FAILED"
    http_status = 502


class TemplateRenderError(EWSGatewayError):
    error_code = "TEMPLATE_RENDER_ERROR"
    http_status = 422


class GatewayCircuitOpenError(EWSGatewayError):
    error_code = "CIRCUIT_OPEN"
    http_status = 503


class WebhookDeliveryError(EWSGatewayError):
    error_code = "WEBHOOK_DELIVERY_ERROR"
    http_status = 502


class EmailNotFoundError(EWSGatewayError):
    error_code = "EMAIL_NOT_FOUND"
    http_status = 404


async def ews_exception_handler(request: Request, exc: EWSGatewayError) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error_code": exc.error_code,
            "message": exc.message or str(exc),
            "request_id": request_id,
        },
    )
```

> **兼容性说明**: 通过 `DoesNotExistHandle = does_not_exist_handle` 等别名保持向后兼容，所有现有 import 无需修改。

---

## 改进 #6：菜单初始化幂等化

### 现状问题

**文件**: `app/core/init_app.py` → `init_menus()` 函数（第 98-264 行）

当前使用 多层嵌套 `try/except/get/create` 模式，冗长且脆弱：

```python
# 约 160 行代码处理 3 个菜单分类
async def get_or_create_catalog(...):
    try:
        catalog = await Menu.get(name=name, parent_id=0)
        catalog.order = order
        ...
        await catalog.save()
    except Exception:
        try:
            catalog = await Menu.create(...)
        except IntegrityError:
            catalog = await Menu.get(name=name, parent_id=0)
            ...
```

### 改进方案

使用 Tortoise ORM 的 `update_or_create()` 方法替换整个 `init_menus()`：

**删除**: 第 98-264 行（整个 `init_menus()` 函数及其内部函数定义）
**替换为**:

```python
async def init_menus():
    """初始化菜单，使用 update_or_create 保证幂等和并发安全。"""

    async def upsert_catalog(name: str, path: str, order: int, icon: str, redirect: str) -> Menu:
        catalog, _ = await Menu.update_or_create(
            defaults={
                "menu_type": MenuType.CATALOG,
                "path": path,
                "order": order,
                "icon": icon,
                "is_hidden": False,
                "component": "Layout",
                "keepalive": False,
                "redirect": redirect,
            },
            name=name,
            parent_id=0,
        )
        return catalog

    async def upsert_child(parent_id: int, child: dict) -> None:
        await Menu.update_or_create(
            defaults={
                "menu_type": MenuType.MENU,
                "path": child["path"],
                "order": child["order"],
                "icon": child["icon"],
                "is_hidden": False,
                "component": child["component"],
                "keepalive": False,
            },
            name=child["name"],
            parent_id=parent_id,
        )

    # 1. 邮件服务
    exchange_menu = await upsert_catalog(
        name="邮件服务",
        path="/exchange",
        order=2,
        icon="ph:envelope-simple-open-bold",
        redirect="/exchange/accounts",
    )

    exchange_children = [
        {
            "name": "账户管理",
            "path": "accounts",
            "component": "/exchange/accounts",
            "icon": "material-symbols:contact-mail-outline",
            "order": 1,
        },
        {
            "name": "API密钥",
            "path": "keys",
            "component": "/exchange/keys",
            "icon": "material-symbols:key-outline",
            "order": 2,
        },
        {
            "name": "Webhook 订阅",
            "path": "webhooks",
            "component": "/exchange/webhooks",
            "icon": "mdi:webhook",
            "order": 3,
        },
        {
            "name": "邮件模板",
            "path": "templates",
            "component": "/exchange/templates",
            "icon": "material-symbols:article-outline",
            "order": 4,
        },
        {
            "name": "操作日志",
            "path": "logs",
            "component": "/exchange/logs",
            "icon": "material-symbols:history",
            "order": 5,
        },
        {
            "name": "使用统计",
            "path": "stats",
            "component": "/exchange/stats",
            "icon": "material-symbols:analytics-outline",
            "order": 6,
        },
        {
            "name": "开发者指南",
            "path": "developer",
            "component": "/developer",
            "icon": "material-symbols:help-outline",
            "order": 7,
        },
    ]

    for child in exchange_children:
        await upsert_child(exchange_menu.id, child)

    # 2. 系统管理
    system_menu = await upsert_catalog(
        name="系统管理",
        path="/system",
        order=1,
        icon="carbon:gui-management",
        redirect="/system/user",
    )

    system_children = [
        {
            "name": "用户管理",
            "path": "user",
            "order": 1,
            "icon": "material-symbols:person-outline-rounded",
            "component": "/system/user",
        },
        {"name": "角色管理", "path": "role", "order": 2, "icon": "carbon:user-role", "component": "/system/role"},
        {
            "name": "菜单管理",
            "path": "menu",
            "order": 3,
            "icon": "material-symbols:list-alt-outline",
            "component": "/system/menu",
        },
        {"name": "API管理", "path": "api", "order": 4, "icon": "ant-design:api-outlined", "component": "/system/api"},
        {
            "name": "部门管理",
            "path": "dept",
            "order": 5,
            "icon": "mingcute:department-line",
            "component": "/system/dept",
        },
        {
            "name": "审计日志",
            "path": "auditlog",
            "order": 6,
            "icon": "ph:clipboard-text-bold",
            "component": "/system/auditlog",
        },
    ]

    for child in system_children:
        await upsert_child(system_menu.id, child)
```

> **注意**: "开发者指南" 菜单从独立的"开发者服务"顶级目录移至"邮件服务"子菜单下（与 feishu-extension 版本一致），减少顶栏目录数量。

同时修改 `init_roles()` 中 silent `except Exception: pass` 为有日志的版本：

**删除**: 第 338-339 行、344-345 行、350-351 行、356-357 行的 `except Exception: pass`
**替换为**:

```python
    except Exception as e:
        logger.warning(f"Failed to assign APIs to admin role: {e}")
```

（每个 `except` 块同理，加上合适的描述信息）

---

## 改进 #7：Docker Compose 安全加固

### 现状问题

**文件**: `docker-compose.yml`

1. **密码硬编码**: `MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-root123}` — 明文默认密码
2. **Worker 无健康检查**: `healthcheck: disable: true`
3. **无资源限制**: app / arq-worker 未设置 CPU / 内存限制
4. **Redis 无密码**: 任何 backend 网络内的容器可直接访问
5. **LOGS_ROOT 重复**: arq-worker 中 `LOGS_ROOT` 声明了两次（第 137-138 行）
6. **无 Docker Secrets**: 敏感信息通过环境变量明文传递

### 改进方案

**完整替换** `docker-compose.yml`，关键改动：

```yaml
# 1. 使用 Docker Secrets 管理密码
secrets:
  secret_key:
    file: ./secrets/secret_key
  exchange_encryption_key:
    file: ./secrets/exchange_encryption_key
  database_url:
    file: ./secrets/database_url
  db_password:
    file: ./secrets/db_password

# 2. MySQL 使用 secret 文件 而非环境变量
mysql:
  environment:
    MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_password
  secrets:
    - db_password

# 3. Worker 添加健康检查
webhook-worker:
  healthcheck:
    test: ["CMD-SHELL", "python -c \"import time; t=float(open('/tmp/worker_heartbeat').read()); assert time.time()-t<60\" 2>/dev/null || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s

arq-worker:
  healthcheck:
    # 同上

# 4. 添加资源限制
app:
  deploy:
    resources:
      limits:
        cpus: "2"
        memory: 2G
      reservations:
        memory: 512M

arq-worker:
  deploy:
    resources:
      limits:
        cpus: "1"
        memory: 1G

# 5. MySQL / Redis 使用 profiles（允许外部服务）
mysql:
  profiles:
    - local-db

redis:
  profiles:
    - local-redis

# 6. 添加日志配置
x-default-logging: &default-logging
  driver: json-file
  options:
    max-size: "50m"
    max-file: "3"

# 7. 修复 LOGS_ROOT 重复
# 8. 删除 arq-worker 第 138 行重复的 LOGS_ROOT
```

**同时需要**:
- 创建 `scripts/init-secrets.sh` 脚本（用于首次部署生成 secrets 文件）
- 更新 `.env.example` 中的说明（见"环境配置简化"章节）

---

## 改进 #8：EWS 异步辅助工具

### 现状问题

`exchangelib` 是同步阻塞库，当前项目使用 `asyncio.to_thread()` 或 `loop.run_in_executor()` 包装，但缺少：
- 专用线程池（与其他 IO 任务共享默认线程池会导致饥饿）
- 并发信号量控制（防止线程池 + EWS 连接池同时过载）
- 超时保护（EWS 操作卡死时无法取消）

### 改进方案

#### 新建 `app/utils/async_helpers.py`

```python
"""Async helpers for running blocking operations safely."""

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

# 专用 EWS 线程池，大小与连接池对齐
# 默认 20 线程 = max_connections_per_account(5) * 预期活跃账户数(4)
EWS_MAX_WORKERS: int = int(os.getenv("EWS_MAX_WORKERS", "20"))
EWS_MAX_CONCURRENT: int = int(os.getenv("EWS_MAX_CONCURRENT", "20"))

_ews_executor = ThreadPoolExecutor(
    max_workers=EWS_MAX_WORKERS,
    thread_name_prefix="ews",
)

# 信号量限制并发 EWS 操作数，防止线程池 + 连接池同时过载
_ews_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """懒加载信号量，确保在事件循环启动后创建。"""
    global _ews_semaphore
    if _ews_semaphore is None:
        _ews_semaphore = asyncio.Semaphore(EWS_MAX_CONCURRENT)
    return _ews_semaphore


async def run_sync_with_timeout(func: Callable[..., Any], *args: Any, timeout: float = 30.0, **kwargs: Any) -> Any:
    """在专用 EWS 线程池中运行同步函数，带超时和并发保护。"""
    loop = asyncio.get_running_loop()
    bound = partial(func, *args, **kwargs)
    async with _get_semaphore():
        return await asyncio.wait_for(
            loop.run_in_executor(_ews_executor, bound),
            timeout=timeout,
        )
```

> **注意**: 新建文件后，需要在使用 `exchangelib` 的 service 文件（如 `app/services/exchange/` 下的文件）中，将现有的 `asyncio.to_thread()` 或 `loop.run_in_executor()` 替换为 `run_sync_with_timeout()`。这属于可选的渐进式重构，不影响主体功能。

---

## 改进 #9：Redis 分布式速率限制器

### 现状问题

**文件**: `app/core/api_key_auth.py` 第 16-24 行

当前代码尝试 import 不存在的 `redis_rate_limiter` 模块，触发 runtime 错误：

```python
try:
    from app.core.redis_rate_limiter import get_rate_limiter
    _rate_limiter = None  # Lazy initialization
except ImportError:
    from app.core.rate_limiter import get_rate_limiter as get_mem_rate_limiter
    _rate_limiter = get_mem_rate_limiter()
```

**问题**: `redis_rate_limiter.py` 不存在于 `exchange-gateway-old`，但 import 并没有真正失败（因为没有实际调用），导致 `_rate_limiter` 始终为 `None`，运行时懒加载逻辑复杂且容易出错。

### 改进方案

#### 步骤 1：新建 `app/core/redis_rate_limiter.py`

从 `exchange-feishu-extension` 完整复制（见前文"改进 #1"中已列出的源码），完整内容：

```python
"""Redis 滑动窗口速率限制器。

使用有序集合（ZSET）实现 O(log N) 的每请求速率限制。
每个请求以时间戳为 score 存储，窗口清理删除超出时间范围的条目。
"""

import time
import uuid

import structlog

logger = structlog.get_logger(__name__)


class RedisRateLimiter:
    """基于 Redis 有序集合的分布式滑动窗口速率限制器。"""

    def __init__(self, redis):
        self._redis = redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """检查请求是否在速率限制内。

        Returns:
            (is_allowed, current_count, remaining)
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        # 清理窗口外的旧条目
        await self._redis.zremrangebyscore(redis_key, "-inf", window_start)

        # 统计当前窗口内的请求数
        current_count = await self._redis.zcard(redis_key)

        if current_count >= limit:
            return False, current_count, 0

        # 记录本次请求（用 uuid 防止重复 member）
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        await self._redis.zadd(redis_key, {member: now})
        await self._redis.expire(redis_key, window_seconds + 10)

        current_count += 1
        remaining = max(0, limit - current_count)
        return True, current_count, remaining


# 模块级实例，在应用启动时设置
_rate_limiter: RedisRateLimiter | None = None


def get_rate_limiter() -> "RedisRateLimiter":
    """获取已初始化的速率限制器。必须在 init_rate_limiter() 之后调用。"""
    if _rate_limiter is None:
        # Redis 不可用时回退到内存限制器
        from app.core.rate_limiter import get_rate_limiter as get_mem_limiter

        return get_mem_limiter()
    return _rate_limiter


async def init_rate_limiter() -> None:
    """初始化 Redis 速率限制器。在应用启动时调用。"""
    global _rate_limiter
    try:
        import redis.asyncio as aioredis

        from app.settings.config import settings

        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        _rate_limiter = RedisRateLimiter(redis=redis_client)
        logger.info("Redis 速率限制器已初始化")
    except Exception as e:
        logger.warning("Redis 不可用，使用内存速率限制器作为回退", error=str(e))
        _rate_limiter = None  # get_rate_limiter() 将回退到内存实现
```

#### 步骤 2：修改 `app/core/init_app.py` 的 `init_data()` 函数

在 `init_data()` 末尾添加 Redis 速率限制器初始化：

```diff
 async def init_data():
     await init_db()
     await init_superuser()
     await init_menus()
     await init_apis()
     await init_roles()
+    # 初始化 Redis 速率限制器
+    from app.core.redis_rate_limiter import init_rate_limiter
+
+    await init_rate_limiter()
```

---

## 改进 #10：API Key 认证模块优化

### 现状问题

**文件**: `app/core/api_key_auth.py`

1. **时区处理不一致**（第 84-93 行）：使用 `datetime.now()` + `.astimezone()` 混合模式
2. **并发更新丢失**（第 146-148 行）：使用 `api_key.usage_count += 1; await api_key.save()` 而非原子操作
3. **速率限制器 import 混乱**（第 16-24 行 + 第 115-126 行）：重复的 try/except import

### 改进方案

**完整替换** `app/core/api_key_auth.py` 的以下部分：

#### 修改 1：import 区域（第 1-24 行）

```diff
-from datetime import datetime
-from typing import Optional
+from datetime import UTC, datetime

-from fastapi import Header, HTTPException, Request
+from fastapi import Header, HTTPException, Request

-from app.log import logger
+from app.core.redis_rate_limiter import get_rate_limiter
+from app.log import logger
 from app.models.exchange import ExchangeApiKey
 from app.utils.crypto import hash_api_key

-# Use Redis rate limiter for distributed deployments
-try:
-    from app.core.redis_rate_limiter import get_rate_limiter
-
-    _rate_limiter = None  # Lazy initialization
-except ImportError:
-    # Fallback to in-memory rate limiter if Redis unavailable
-    from app.core.rate_limiter import get_rate_limiter as get_mem_rate_limiter
-
-    _rate_limiter = get_mem_rate_limiter()
```

#### 修改 2：`__init__` 类型标注（第 40-41 行）

```diff
-    def __init__(self, required_permissions: Optional[list[str]] = None, auto_error: bool = True):
+    def __init__(self, required_permissions: list[str] | None = None, auto_error: bool = True):
```

#### 修改 3：`__call__` 签名（第 51-55 行）

```diff
     async def __call__(
         self,
         request: Request,
-        x_api_key: Optional[str] = Header(None, alias="X-Api-Key", description="API 密钥"),
-    ) -> Optional[ExchangeApiKey]:
+        x_api_key: str | None = Header(None, alias="X-Api-Key", description="API 密钥"),
+    ) -> ExchangeApiKey | None:
```

#### 修改 4：过期时间检查（第 83-93 行）

```diff
             # 3. 检查过期时间
             if api_key.expires_at:
-                now = datetime.now()
-                # 如果数据库存的是带时区的时间，则将当前时间也转换为带时区
-                if api_key.expires_at.tzinfo:
-                    now = now.astimezone()
+                now = datetime.now(tz=UTC)
+                expires = api_key.expires_at
+                if expires.tzinfo is None:
+                    expires = expires.replace(tzinfo=UTC)

-                if api_key.expires_at < now:
+                if expires < now:
```

#### 修改 5：速率限制器调用（第 113-126 行）

```diff
             # 6. 检查速率限制
-            # 使用懒加载获取 rate limiter
-            global _rate_limiter
-            if _rate_limiter is None:
-                try:
-                    from app.core.redis_rate_limiter import get_rate_limiter as get_redis_rate_limiter
-
-                    _rate_limiter = get_redis_rate_limiter()
-                except Exception:
-                    from app.core.rate_limiter import get_rate_limiter as get_mem_rate_limiter
-
-                    _rate_limiter = get_mem_rate_limiter()
-
-            rate_limiter = _rate_limiter
+            rate_limiter = get_rate_limiter()
```

#### 修改 6：原子更新使用信息（第 145-148 行）

```diff
-            # 7. 更新使用信息
-            api_key.last_used_at = datetime.now()
-            api_key.usage_count += 1
-            await api_key.save()
+            # 7. 原子更新使用信息，避免并发计数丢失
+            from tortoise.expressions import F
+
+            await ExchangeApiKey.filter(id=api_key.id).update(
+                last_used_at=datetime.now(tz=UTC),
+                usage_count=F("usage_count") + 1,
+            )
```

#### 修改 7：`_get_client_ip` 方法 → 模块级函数（删除第 164-177 行的 `_get_client_ip` 方法）

将 `_get_client_ip` 实例方法引用改为模块级函数 `get_client_ip`（已存在于第 180-190 行），确保第 97 行的调用一致：

```diff
-                client_ip = self._get_client_ip(request)
+                client_ip = get_client_ip(request)
```

---

## 改进 #11：依赖注入与权限模块优化

### 现状问题

**文件**: `app/core/dependency.py`

1. **structlog 未集成**（第 89 行）：使用 `f"..."` 字符串插值记录异常，无 structured logging
2. **N+1 查询**（第 109-110 行）：`await role.apis` 未使用 `prefetch_related`
3. **低效的权限收集**（第 110 行）：`list(set(... for api in sum(apis, [])))` 嵌套低效
4. **泄露异常详情**（第 89 行）：`detail=f"{repr(e)}"` 泄露内部异常

### 改进方案

#### 修改 1：import 添加 structlog（第 1-11 行）

```diff
 from typing import Optional

 import jwt
+import structlog
 from fastapi import Depends, Header, HTTPException, Request

 from app.core.ctx import CTX_USER_ID
-from app.models import Role, User, ExchangeApiKey
+from app.models import ExchangeApiKey, Role, User
 from app.settings import settings
 from app.utils.crypto import hash_api_key
+
+logger = structlog.get_logger(__name__)
```

#### 修改 2：异常处理（第 88-89 行）

```diff
         except Exception as e:
-            raise HTTPException(status_code=500, detail=f"{repr(e)}")
+            logger.error("Authentication error", error=repr(e))
+            raise HTTPException(status_code=500, detail="认证服务内部错误")
```

#### 修改 3：权限查询优化（第 106-110 行）

```diff
-        roles: list[Role] = await current_user.roles
+        roles: list[Role] = await current_user.roles.all().prefetch_related("apis")
         if not roles:
             raise HTTPException(status_code=403, detail="The user is not bound to a role")
-        apis = [await role.apis for role in roles]
-        permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))
+        permission_apis = {(api.method, api.path) for role in roles for api in role.apis}
```

#### 修改 4：权限拒绝日志（第 115 行）

```diff
-            logger.warning(f"Permission denied: method={method}, path={path}, roles={[r.name for r in roles]}")
+            logger.warning("Permission denied", method=method, path=path, roles=[r.name for r in roles])
```

---

## 改进 #12：日志模块增强

### 现状问题

**文件**: `app/core/logging.py`

当前仅绑定了 `structlog` 自己的 root logger，未捕获第三方库（`exchangelib`, `tortoise`, `uvicorn`）的日志。

### 改进方案

在 `configure_logging()` 末尾添加根 logger 捕获（第 59 行后）：

```diff
     structlog_root.propagate = False

+    # 捕获根 logger，使第三方库（exchangelib、tortoise、uvicorn）也通过 structlog 输出
+    root = logging.getLogger()
+    root.handlers = [handler]
+    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
```

---

## 改进 #13：`crypto.py` 补充常量时间比较

### 现状问题

**文件**: `app/utils/crypto.py`

缺少 `verify_api_key_hash()` 函数（常量时间比较，防止 timing attack）。

### 改进方案

在文件末尾添加：

```python
def verify_api_key_hash(api_key: str, expected_hash: str) -> bool:
    """
    常量时间比较 API 密钥哈希，防止 timing attack。

    Args:
        api_key: 原始 API 密钥
        expected_hash: 数据库中存储的哈希值

    Returns:
        是否匹配
    """
    import hmac

    computed = hash_api_key(api_key)
    return hmac.compare_digest(computed, expected_hash)
```

---

## 环境配置简化

### 删除多环境模式

**文件**: `app/settings/config.py`

当前 `DEV_MODE` 逻辑增加了理解成本。简化为：
- **环境变量为空 → 启动报错并给出清晰提示**
- **无 DEV_MODE 概念**

#### `config.py` 主要修改

1. **删除** `DEV_MODE` 变量和 `_DEV_SECRET_KEY` / `_DEV_DB_PASSWORD` 常量
2. **删除** `model_validator` 中的 DEV_MODE 分支逻辑
3. **保留** `ENV` 变量（仅用于控制日志输出格式 JSON vs Console）
4. **SECRET_KEY 和 EXCHANGE_ENCRYPTION_KEY** 仅从环境变量读取
5. **修改** `get_secret()` 函数，使空值返回空字符串（而非 `default or default` 的逻辑）

#### `.env.example` 简化

```ini
# ===========================================
# Exchange Gateway Configuration
# ===========================================
# Copy this file and rename to .env, then modify settings below
# cp .env.example .env

# ===========================================
# Exchange Server (Required)
# ===========================================
EXCHANGE_SERVER=your-exchange-server
EXCHANGE_DOMAIN=your-domain
EXCHANGE_EMAIL_SUFFIX=@your-domain.com

# ===========================================
# Database (Required)
# ===========================================
# Format: mysql://user:password@host:port/database
DATABASE_URL=mysql://root:changeme@mysql:3306/exchange_gateway

# ===========================================
# Security (Required - generate before first run)
# ===========================================
# Generate: openssl rand -hex 32
SECRET_KEY=changeme

# Generate: python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
EXCHANGE_ENCRYPTION_KEY=changeme

# ===========================================
# Optional Settings
# ===========================================
# WORKERS=2
# BACKEND_PORT=8000
# NGINX_PORT=80
# REDIS_URL=redis://redis:6379/0
# CORS_ORIGINS=http://localhost:3000,http://localhost:5173
# AUTO_MIGRATE=true
```

---

## 开源标准化

### 需要删除的文件

| 文件/目录 | 原因 |
|:--|:--|
| `CLAUDE.md` | AI 辅助工具配置 |
| `DEPLOYMENT_SUMMARY.md` | 内部部署记录 |
| `docker_logs.txt`（如存在） | 调试产物 |
| `pytest_failures.txt`（如存在） | 调试产物 |

### 需要更新的文件

| 文件 | 修改内容 |
|:--|:--|
| `README.md` | 简化为英文 Quick Start + Architecture + API docs |
| `CHANGELOG.md` | 重置为 v1.0.0 首次发布 |
| `.gitignore` | 添加 `secrets/` 目录 |

### 新增文件

| 文件 | 内容 |
|:--|:--|
| `scripts/init-secrets.sh` | 首次部署生成 secrets 文件 |

---

## 测试用例要求

> ⚠️ **非常重要**: 每项改进必须有对应的测试用例。以下是需要编写的测试清单。

### 现有测试基础

- 测试框架: `pytest` + `pytest-asyncio`
- 配置文件: `pytest.ini`
- 测试 DB: SQLite in-memory（`tests/conftest.py`）
- 现有单元测试: `tests/unit/` 下 12 个文件
- 运行命令: `cd /opt/app && python -m pytest tests/ -v`

### 新增测试清单

#### 1. Migration Lock 测试 — `tests/unit/test_migration_lock.py`

```
测试目标: app/utils/migration_lock.py
测试内容:
  - test_acquire_success: 首次 acquire 返回 True
  - test_acquire_already_held: 已持有锁时 acquire 返回 False
  - test_release: release 后可重新 acquire
  - test_wait_for_completion: 等待锁释放后返回
  - test_wait_for_completion_timeout: 超时后返回并记录 warning
方式: 使用 fakeredis 或 mock Redis client
```

#### 2. 敏感数据脱敏测试 — `tests/unit/test_mask_sensitive.py`

```
测试目标: app/core/middlewares._mask_sensitive()
测试内容:
  - test_mask_password: {"password": "secret123"} → {"password": "***"}
  - test_mask_nested: 嵌套字典中的敏感字段也被脱敏
  - test_mask_case_insensitive: "Password" 和 "PASSWORD" 都被脱敏
  - test_non_sensitive_preserved: 非敏感字段保持原值
  - test_mask_list_of_dicts: 列表中的字典也被递归脱敏
  - test_non_dict_passthrough: 非字典输入直接返回
```

#### 3. 异常体系测试 — 更新 `tests/unit/test_exceptions.py`

```
测试目标: app/core/exceptions.py
测试内容:
  - test_does_not_exist_no_leak: 确认响应中不包含内部异常详情
  - test_integrity_no_leak: 确认响应中不包含 SQL 详情
  - test_new_exception_types: 验证 AttachmentTooLargeError、WebhookDeliveryError、EmailNotFoundError 的 error_code 和 http_status
  - test_ews_exception_handler_request_id: 确认 request_id 被正确传递
  - test_backward_compat_aliases: EWSGatewayException == EWSGatewayError, DoesNotExistHandle == does_not_exist_handle
```

#### 4. Redis 速率限制器测试 — `tests/unit/test_redis_rate_limiter.py`

```
测试目标: app/core/redis_rate_limiter.py
测试内容:
  - test_is_allowed_within_limit: 未超限时返回 (True, count, remaining)
  - test_is_allowed_exceeds_limit: 超限时返回 (False, count, 0)
  - test_window_expiry: 窗口过期后计数归零
  - test_fallback_to_memory: Redis 不可用时回退到内存限制器
方式: 使用 fakeredis 或 mock
```

#### 5. API Key 认证测试 — `tests/unit/test_api_key_auth.py`

```
测试目标: app/core/api_key_auth.py
测试内容:
  - test_utc_expiry_check: 确认基于 UTC 的过期判断正确
  - test_atomic_usage_count: 确认使用 F expression 更新
  - test_verify_account_access: 确认账户访问控制逻辑
方式: 使用 pytest + mock
```

#### 6. 异步辅助工具测试 — `tests/unit/test_async_helpers.py`

```
测试目标: app/utils/async_helpers.py
测试内容:
  - test_run_sync_basic: 同步函数在线程池中正确执行
  - test_run_sync_timeout: 超时时抛出 asyncio.TimeoutError
  - test_semaphore_concurrency: 并发数不超过 EWS_MAX_CONCURRENT
方式: 使用 pytest-asyncio
```

#### 7. 菜单初始化幂等性测试 — `tests/unit/test_init_menus.py`

```
测试目标: app/core/init_app.init_menus()
测试内容:
  - test_init_menus_creates_all: 首次运行创建所有菜单
  - test_init_menus_idempotent: 重复运行不创建重复菜单
  - test_init_menus_updates_order: 修改 order 后重新运行会更新
方式: 使用 SQLite in-memory（复用 conftest.py）
```

#### 8. Docker Compose 结构测试 — `tests/unit/test_compose_structure.py`

```
测试目标: docker-compose.yml
测试内容:
  - test_no_hardcoded_passwords: 确认无明文密码
  - test_workers_have_healthcheck: 确认 worker 有健康检查
  - test_resource_limits_exist: 确认 deploy.resources 存在
  - test_no_duplicate_env_vars: 确认无重复环境变量
方式: 使用 PyYAML 解析 docker-compose.yml
```

#### 9. Crypto 测试 — 更新 `tests/unit/test_crypto.py`

```
新增测试内容:
  - test_verify_api_key_hash_match: 正确密钥返回 True
  - test_verify_api_key_hash_mismatch: 错误密钥返回 False
  - test_verify_api_key_hash_timing_safe: 确认使用 hmac.compare_digest
```

### 运行所有测试的命令

```bash
# 在 Docker 容器内
docker compose exec app python -m pytest tests/ -v --tb=short

# 本地开发（需要安装依赖）
python -m pytest tests/ -v --tb=short

# 只运行新增测试
python -m pytest tests/unit/test_migration_lock.py tests/unit/test_mask_sensitive.py tests/unit/test_redis_rate_limiter.py tests/unit/test_async_helpers.py tests/unit/test_init_menus.py tests/unit/test_compose_structure.py -v
```

---

## 实施优先级和依赖关系

```
Phase 1（基础设施）—— 无依赖
  ├── #1 Redis 分布式迁移锁
  ├── #8 EWS 异步辅助工具
  └── #9 Redis 分布式速率限制器

Phase 2（安全加固）—— 依赖 Phase 1 中的 #9
  ├── #2 审计日志脱敏
  ├── #3 审计日志 structlog
  ├── #4 中间件用户识别
  ├── #5 异常体系扩展
  ├── #10 API Key 认证优化
  ├── #11 依赖注入优化
  ├── #12 日志模块增强
  └── #13 crypto 常量时间比较

Phase 3（架构优化）—— 依赖 Phase 2
  ├── #6 菜单初始化幂等化
  └── #7 Docker Compose 安全加固

Phase 4（开源准备）—— 依赖 Phase 3
  ├── 环境配置简化
  ├── 开源标准化
  └── 编写全部测试用例
```
