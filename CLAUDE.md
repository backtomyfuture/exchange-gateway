# Exchange 项目会话重点记录（本次）

## 1. 目标与背景
- 目标：修复并稳定 Exchange Webhook 链路，明确事件订阅策略，并给客户端对接提供可执行参考。
- 部署：`docker-compose.dev.yml`（本地测试）与 `docker-compose.yml`（生产）。
- 执行约束：测试统一使用本地 `.venv`。

## 2. 关键问题与结论

### 2.1 Webhook URL 被拦截内网 IP
- 现象：创建 webhook 使用内网地址时触发校验错误（禁止内部网络地址）。
- 结论：生产环境默认拦截是合理的 SSRF 安全基线；开发环境需要可控放开。
- 处理：
  - 新增配置：`WEBHOOK_ALLOW_PRIVATE_URLS`
  - 默认策略：`DEV_MODE=true` 时默认允许；非开发默认禁止
  - 仍始终禁止：`localhost/127.0.0.1/::1` 与 link-local
- 相关文件：
  - `app/settings/config.py`
  - `app/schemas/webhook.py`
  - `docker-compose.dev.yml`

### 2.2 webhook-worker 报错：`unexpected keyword argument 'folders'`
- 现象：日志持续出现 `Account.subscribe_to_streaming() got an unexpected keyword argument 'folders'`。
- 根因：`exchangelib==5.4.1` 下该调用参数不匹配。
- 修复路径（最终）：
  - 按 `exchangelib` 正确 streaming 流程改造：
    1) `subscribe_to_streaming`
    2) `get_streaming_events`
  - 严格按库行为，不保留临时兼容分支。
- 相关文件：
  - `app/services/exchange/webhook_listener.py`
  - `tests/unit/test_webhook_listener_subscription.py`

### 2.3 订阅策略改造（按你的要求）
- 要求：不做文件夹筛选，全量监听；事件支持白名单。
- 落地：
  - 改为全邮箱订阅（不再限 Inbox）
  - 事件白名单默认仅：`NewMailEvent`
  - 支持事件别名规范化（如 `NewMail -> NewMailEvent`）
  - 支持 `*`（全部事件）
  - 分发前按 webhook 的 `events` 精确过滤
- 相关文件：
  - `app/services/exchange/webhook_listener.py`
  - `app/schemas/webhook.py`
  - `tests/unit/test_webhook_schema.py`
  - `tests/unit/test_webhook_listener_subscription.py`

### 2.4 webhook secret 解密失败（`webhook id=4`）
- 现象：`Failed to decrypt secret for webhook 4`。
- 排查结果：
  - DB 中 `id=4` 的密文无法被当前 `EXCHANGE_ENCRYPTION_KEY` 解密
  - `id=6` 可正常解密并正常推送
- 处理：
  - 已将 `id=4` 设为禁用，避免持续报错污染日志
  - 当前启用项中可解密项正常

## 3. 客户端对接规范（当前实现）

### 3.1 Webhook 回调（服务端 -> 客户端）
- 方法：`POST`
- Headers：
  - `Content-Type: application/json`
  - `X-Exchange-Event: <事件名>`
  - `X-Exchange-Signature: <HMAC-SHA256 hex>`
- Body（metadata）：
  - `account_id`
  - `event`（例如 `NewMailEvent`）
  - `event_type`
  - `item_id`（对象结构：`{id, changekey}`）
  - `folder_id`（对象结构：`{id, changekey}`，若有）
  - `watermark`
  - `unread_count`
  - `old_item_id` / `old_folder_id` / `parent_folder_id` 等（对象结构，视事件类型而定）
  - ...（及 exchangelib 事件对象的所有其他原始属性）

### 3.2 推荐处理流程（客户端）
1. 验签（用原始 body 字节）
2. 白名单过滤（当前关注 `NewMailEvent`）
3. 幂等去重（建议键：`account_id + event + item_id`）
4. 快速返回 `200`，异步处理
5. 按 `item_id` 调邮件详情 API 拉取正文/附件等

### 3.3 邮件详情 API（客户端拉取）
- 路由：`GET /api/v1/exchange/emails/{email_id}?account_id=<id>`
- 鉴权：`X-Api-Key`（需 `receive` 权限）
- 返回外层格式：`{ code, msg, data }`

### 3.4 文件夹 ID API（客户端拉取）
- 路由：`GET /api/v1/exchange/emails/folders/all?account_id=<id>`
- 鉴权：`X-Api-Key`（需 `folders` 权限）
- 作用：获取所有文件夹（包含标准文件夹 `Inbox`, `Sent` 等及自定义文件夹）的 ID、ChangeKey 和层级关系。
- 场景：接收到 Webhook `folder_id` 或 `parent_folder_id` 时，由此接口查询对应的文件夹名称。

## 4. 日志验证结果（本次）
- 两封测试邮件均触发：
  - `Event: NewMailEvent`
  - `Webhook success: http://10.78.14.164:15000/webhooks/exchange`
- 最近窗口内无新的 `Webhook failed`/`decrypt failed`（历史 `id=4` 异常已隔离）。

## 5. 测试与质量检查
- 单测命令（均使用 `.venv`）：
  - `.venv/bin/pytest tests/unit/test_webhook_listener_subscription.py tests/unit/test_webhook_schema.py -q`
- 结果：通过（本次新增与回归测试均通过）。
- Lint：本次改动文件无新增 linter 错误。

## 6. 现状快照
- 当前有效 webhook：`id=6`（正常）
- 已禁用异常 webhook：`id=4`（secret 解密失败）
- worker 状态：`webhook-worker` 运行正常，能接收并推送 `NewMailEvent`。

## 7. 后续建议（可选）
- 若需恢复 `id=4`：重置 secret 并用当前密钥重新加密后启用。
- 生产环境建议继续保持 `WEBHOOK_ALLOW_PRIVATE_URLS=false`，按需加白名单策略，不建议全量放开。

### 2.5 Exchange 事件说明（开发者参考）

1. **核心事件（最常用）**
   - **NewMailEvent (新邮件到达)**
     - **含义**：表示邮箱（通常是 Inbox）收到了一封新邮件。这是最常用的触发器。
     - **适用场景**：实时接收新邮件通知。
     - **注意**：这通常只针对收件箱。如果是你发出的邮件（在发件箱），或者是通过规则移动到其他文件夹的邮件，可能不会触发此事件。

   - **CreatedEvent (创建)**
     - **含义**：在受监控的文件夹中创建了一个新项目（邮件、日历、联系人等）。
     - **适用场景**：
       - 监控**发件箱 (Sent Items)**：当你发送邮件时，邮件被保存到发件箱，这会触发 CreatedEvent。
       - 监控**草稿箱 (Drafts)**：保存草稿时触发。
       - 监控被规则移动的邮件：如果邮件直接进入了其他文件夹（非 Inbox），可能触发的是 Created 而非 NewMail。

   - **ModifiedEvent (修改)**
     - **含义**：现有的项目被修改了。
     - **适用场景**：
       - 邮件被标记为“已读”或“未读”。
       - 邮件被加了旗标（Flag）。
       - 日历项被更新。
       - 草稿被再次编辑保存。

   - **DeletedEvent (删除)**
     - **含义**：项目被硬删除或移动到“已删除邮件”文件夹（视具体操作而定）。
     - **适用场景**：同步删除操作。

2. **移动与复制事件**
   - **MovedEvent (移动)**
     - **含义**：项目从受监控的文件夹移动到了另一个文件夹。
     - **适用场景**：用户手动归档邮件，或者将邮件拖动到其他文件夹。

   - **CopiedEvent (复制)**
     - **含义**：项目被复制。
     - **适用场景**：较少使用，通常发生在用户手动复制邮件或日历项时。

3. **其他事件**
   - **FreeBusyChangedEvent (忙闲状态变更)**
     - **含义**：用户的忙闲状态（日历可用性）发生变化。
     - **适用场景**：主要用于日历同步应用，感知用户何时有空。

4. **内部事件（不可订阅，但可能收到）**
   - **StatusEvent (状态/心跳)**
     - **含义**：Exchange 服务器发送的心跳包，用于保持连接活跃。
     - **注意**：你不需要显式订阅它，exchangelib 的流式客户端会自动处理它以维持连接。
