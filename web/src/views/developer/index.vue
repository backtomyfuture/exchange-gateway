<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <n-card title="开发者指南" size="small" rounded-10 segmented>
        <template #header-extra>
            <n-button tag="a" href="/docs" target="_blank" type="primary" dashed>
                打开 Swagger API 文档
            </n-button>
        </template>
        
        <n-alert title="关于 Exchange 邮件网关 API" type="info" mb-20>
           提供标准 RESTful API，支持邮件发送/接收/搜索。所有请求需要 API Key 认证，
           并受速率限制保护（默认 100 次/分钟）。<br/>
           注意：生产环境强制使用 HTTPS，如果是自签名证书，请在客户端忽略 SSL 验证（如 curl -k）。
        </n-alert>

        <n-tabs type="line" animated>
          <!-- 1. 认证 -->
          <n-tab-pane name="auth" tab="🔑 认证方式">
            <n-space vertical>
                <div class="text-16 font-bold">获取 API Key</div>
                <ol class="pl-20">
                    <li>进入 <n-tag type="success">Exchange 服务</n-tag> -> <n-tag type="success">API 密钥</n-tag> 菜单</li>
                    <li>点击 <strong>创建密钥</strong>，选择需要的权限</li>
                    <li>复制生成的密钥 <n-tag type="warning">仅显示一次！</n-tag></li>
                </ol>

                <div class="text-16 font-bold mt-20">请求头格式</div>
                <n-code language="http" :code="authHeaderCode" />

                <n-alert type="warning" title="安全提示" class="mt-16">
                  <ul class="pl-20 mb-0">
                    <li>密钥只在创建时显示一次，请妥善保存</li>
                    <li>建议配置 IP 白名单限制调用来源</li>
                    <li>定期轮换密钥以提高安全性</li>
                  </ul>
                </n-alert>
            </n-space>
          </n-tab-pane>

          <!-- 2. 发送邮件 -->
          <n-tab-pane name="send" tab="📤 发送邮件">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/send</n-descriptions-item>
              <n-descriptions-item label="权限">send</n-descriptions-item>
              <n-descriptions-item label="说明">异步发送，立即返回日志ID</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="sendParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonSendCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlSendCode" />
                </n-tab-pane>
                <n-tab-pane name="js" tab="JavaScript">
                    <n-code language="javascript" :code="jsSendCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3. 获取邮件 -->
          <n-tab-pane name="receive" tab="📥 邮件管理">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="列表">GET /api/v1/exchange/emails/list</n-descriptions-item>
              <n-descriptions-item label="详情">GET /api/v1/exchange/emails/{email_id}</n-descriptions-item>
              <n-descriptions-item label="标记">PUT /api/v1/exchange/emails/{email_id}/read</n-descriptions-item>
              <n-descriptions-item label="权限">receive (列表/详情), read (标记)</n-descriptions-item>
            </n-descriptions>
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonReceiveCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlReceiveCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3.6. 文件夹管理 (新增) -->
          <n-tab-pane name="folders" tab="📂 文件夹管理">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">GET /api/v1/exchange/emails/folders/all</n-descriptions-item>
              <n-descriptions-item label="权限">folders</n-descriptions-item>
              <n-descriptions-item label="说明">获取所有文件夹（包括自定义）的 ID、ChangeKey 和层级关系</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="folderParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonFolderCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlFolderCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3.5. 邮件同步 (新增) -->
          <n-tab-pane name="sync" tab="🔁 邮件同步">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/sync</n-descriptions-item>
              <n-descriptions-item label="权限">sync</n-descriptions-item>
              <n-descriptions-item label="说明">获取自上次 sync_state 之后的增量变化，适合轮询同步</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="syncParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonSyncCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlSyncCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3.8. 创建草稿 (新增) -->
          <n-tab-pane name="drafts" tab="📝 创建草稿">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/drafts</n-descriptions-item>
              <n-descriptions-item label="权限">drafts</n-descriptions-item>
              <n-descriptions-item label="说明">创建邮件并保存到草稿箱，不进行发送</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="draftParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonDraftCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlDraftCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3.9. 回复邮件 (新增) -->
          <n-tab-pane name="reply" tab="↩️ 回复邮件">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/reply</n-descriptions-item>
              <n-descriptions-item label="权限">reply</n-descriptions-item>
              <n-descriptions-item label="说明">回复指定邮件，支持回复全部</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="replyParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonReplyCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlReplyCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 3.10. 转发邮件 (新增) -->
          <n-tab-pane name="forward" tab="➡️ 转发邮件">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/forward</n-descriptions-item>
              <n-descriptions-item label="权限">forward</n-descriptions-item>
              <n-descriptions-item label="说明">转发指定邮件，可添加转发附言</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="forwardParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonForwardCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlForwardCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>

          <!-- 4. 搜索邮件 -->
          <n-tab-pane name="search" tab="🔍 搜索邮件">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/search</n-descriptions-item>
              <n-descriptions-item label="权限">search</n-descriptions-item>
            </n-descriptions>
            
            <n-code language="python" :code="pythonSearchCode" />
          </n-tab-pane>
          
          <!-- 5. 模板发送 -->
          <n-tab-pane name="template" tab="📝 模板发送">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">POST /api/v1/exchange/emails/send-template</n-descriptions-item>
              <n-descriptions-item label="权限">send</n-descriptions-item>
              <n-descriptions-item label="变量语法"><code v-pre>{{ 变量名 }}</code></n-descriptions-item>
            </n-descriptions>

            <n-alert type="info" title="模板功能说明" class="mb-16">
              <ul class="pl-20 mb-0">
                <li>在后台「邮件模板」页面创建模板，使用 <code v-pre>{{ name }}</code> 语法定义变量</li>
                <li>调用 API 时传入 <code>variables</code> 参数，系统自动替换变量</li>
                <li>模板支持 HTML 和纯文本两种格式</li>
              </ul>
            </n-alert>

            <div class="text-14 font-bold mb-8">请求参数</div>
            <n-data-table :columns="sendParamColumns" :data="templateParams" :bordered="false" size="small" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonTemplateCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlTemplateCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>
          
          <!-- 6. 通讯录 -->
          <n-tab-pane name="contacts" tab="👥 通讯录">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item label="接口">GET /api/v1/exchange/contacts/resolve</n-descriptions-item>
              <n-descriptions-item label="权限">contacts</n-descriptions-item>
              <n-descriptions-item label="说明">优先搜索个人通讯录，未找到则回退搜索 GAL</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">查询参数</div>
            <n-data-table :columns="sendParamColumns" :data="contactParams" :bordered="false" size="small" class="mb-16" />
            
            <div class="text-14 font-bold mb-8">响应结构</div>
            <n-code language="json" :code="contactResponseCode" class="mb-16" />
            
            <n-tabs type="segment">
                <n-tab-pane name="python" tab="Python">
                    <n-code language="python" :code="pythonContactCode" />
                </n-tab-pane>
                <n-tab-pane name="curl" tab="cURL">
                    <n-code language="bash" :code="curlContactCode" />
                </n-tab-pane>
            </n-tabs>
          </n-tab-pane>
          
          <!-- 7. Webhook -->
          <n-tab-pane name="webhook" tab="🪝 Webhook 回调">
            <n-alert type="info" title="Webhook 说明" class="mb-16">
              <ul class="pl-20 mb-0">
                <li>当有新邮件到达时，系统会向配置的 URL 发送 POST 请求</li>
                <li>请求包含 <strong>X-Exchange-Signature</strong> 头，用于验证请求来源</li>
                <li>失败重试机制：指数退避重试 3 次（间隔 2s, 4s, 8s...）</li>
              </ul>
            </n-alert>

            <div class="text-14 font-bold mb-8">Payload 结构</div>
            <n-code language="json" :code="webhookPayloadCode" class="mb-16" />

            <div class="text-14 font-bold mb-8">签名验证 (Python)</div>
            <n-code language="python" :code="pythonWebhookVerifyCode" />
          </n-tab-pane>

          <!-- 8. 错误处理 -->
           <n-tab-pane name="errors" tab="⚠️ 错误码">
             <n-data-table :columns="errorColumns" :data="errorCodes" :bordered="false" size="small" />
           </n-tab-pane>
        </n-tabs>
      </n-card>
    </div>
  </AppPage>
</template>

<script setup>
import { h } from 'vue'
import { NCode, NTag, NDescriptions, NDescriptionsItem, NDataTable } from 'naive-ui'

// 认证头
const authHeaderCode = `X-API-KEY: your_api_key_here`

// 发送参数表格
const sendParamColumns = [
  { title: '参数', key: 'name', width: 120 },
  { title: '类型', key: 'type', width: 100 },
  { title: '必填', key: 'required', width: 60,
    render: (row) => h(NTag, { type: row.required ? 'error' : 'default', size: 'small' }, 
      { default: () => row.required ? '是' : '否' })
  },
  { title: '说明', key: 'desc' },
]

const sendParams = [
  { name: 'account_id', type: 'int', required: true, desc: '发送账户ID' },
  { name: 'to', type: 'string[]', required: true, desc: '收件人邮箱列表' },
  { name: 'subject', type: 'string', required: true, desc: '邮件主题' },
  { name: 'body', type: 'string', required: true, desc: '邮件正文' },
  { name: 'body_type', type: 'string', required: false, desc: '"text" 或 "html"，默认 "text"' },
  { name: 'cc', type: 'string[]', required: false, desc: '抄送列表' },
  { name: 'bcc', type: 'string[]', required: false, desc: '密送列表' },
  { name: 'attachments', type: 'array', required: false, desc: '附件列表 [{filename, content(base64), content_type}]' },
]

// 同步请求参数
const syncParams = [
  { name: 'account_id', type: 'int', required: true, desc: '账户ID' },
  { name: 'folder', type: 'string', required: false, desc: '文件夹名称，默认 INBOX' },
  { name: 'sync_state', type: 'string', required: false, desc: '上次同步状态字符串（首次为空）' },
  { name: 'limit', type: 'int', required: false, desc: '返回最大数量，默认 100' },
  { name: 'only_fields', type: 'string[]', required: false, desc: '仅同步指定字段' },
]

// 文件夹参数
const folderParams = [
  { name: 'account_id', type: 'int', required: true, desc: '账户ID' },
]

// 文件夹 - Python
const pythonFolderCode = `import requests

API_URL = "https://your-server/api/v1/exchange/emails/folders/all"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY}

response = requests.get(API_URL, params={"account_id": 1}, headers=headers)
folders = response.json()["data"]["folders"]

for f in folders:
    print(f"{f['name']} (ID: {f['id'][:10]}...)")`

// 文件夹 - cURL
const curlFolderCode = `curl -k -G "https://your-server/api/v1/exchange/emails/folders/all" \\
    -H "X-API-KEY: your_api_key_here" \\
    -d "account_id=1"`

// 错误码表格
const errorColumns = [
  { title: '状态码', key: 'code', width: 100,
    render: (row) => h(NTag, { type: row.type, size: 'small' }, { default: () => row.code })
  },
  { title: '说明', key: 'desc' },
  { title: '处理建议', key: 'action' },
]

const errorCodes = [
  { code: '200', type: 'success', desc: '请求成功', action: '正常处理响应数据' },
  { code: '401', type: 'error', desc: 'API Key 无效或已过期', action: '检查密钥是否正确或重新生成' },
  { code: '403', type: 'error', desc: '权限不足或 IP 不在白名单', action: '检查密钥权限配置' },
  { code: '404', type: 'warning', desc: '模板不存在或已禁用', action: '检查模板ID是否正确' },
  { code: '422', type: 'warning', desc: '参数验证失败', action: '检查请求参数格式' },
  { code: '429', type: 'warning', desc: '请求频率超限', action: '降低请求频率或申请提高限额' },
  { code: '500', type: 'error', desc: '服务器内部错误', action: '稍后重试或联系管理员' },
]

// 模板发送参数
const templateParams = [
  { name: 'template_id', type: 'int', required: true, desc: '模板ID（在后台查看）' },
  { name: 'account_id', type: 'int', required: true, desc: '发送账户ID' },
  { name: 'to', type: 'string[]', required: true, desc: '收件人邮箱列表' },
  { name: 'variables', type: 'object', required: false, desc: '变量替换 {"name": "value"}' },
  { name: 'cc', type: 'string[]', required: false, desc: '抄送列表' },
  { name: 'bcc', type: 'string[]', required: false, desc: '密送列表' },
  { name: 'attachments', type: 'array', required: false, desc: '附件列表' },
]

// Python 发送示例
const pythonSendCode = `import requests
import base64

API_URL = "https://your-server/api/v1/exchange/emails/send"
API_KEY = "your_api_key_here"

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# 发送 HTML 邮件（带附件）
with open("report.pdf", "rb") as f:
    attachment_b64 = base64.b64encode(f.read()).decode()

data = {
    "account_id": 1,
    "to": ["recipient@example.com"],
    "subject": "月度报告",
    "body": "<h1>月度报告</h1><p>详见附件</p>",
    "body_type": "html",
    "cc": ["manager@example.com"],
    "attachments": [{
        "filename": "report.pdf",
        "content": attachment_b64,
        "content_type": "application/pdf"
    }]
}

response = requests.post(API_URL, json=data, headers=headers)
result = response.json()

if result.get("code") == 200:
    print(f"发送成功，日志ID: {result['data']['log_id']}")
else:
    print(f"发送失败: {result.get('msg')}")`

// cURL 发送示例
const curlSendCode = `curl -k -X POST "https://your-server/api/v1/exchange/emails/send" \\
     -H "X-API-KEY: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
           "account_id": 1,
           "to": ["user@example.com"],
           "subject": "测试邮件",
           "body": "<h1>标题</h1><p>正文内容</p>",
           "body_type": "html"
         }'`

// JavaScript 发送示例
const jsSendCode = `const API_URL = 'https://your-server/api/v1/exchange/emails/send'
const API_KEY = 'your_api_key_here'

async function sendEmail() {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'X-API-KEY': API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      account_id: 1,
      to: ['recipient@example.com'],
      subject: '测试邮件',
      body: '<h1>Hello</h1><p>This is a test.</p>',
      body_type: 'html',
    }),
  })
  
  const result = await response.json()
  console.log(result)
}

sendEmail()`

// Python 接收示例
const pythonReceiveCode = `import requests

API_URL = "https://your-server/api/v1/exchange/emails"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY}

# 获取收件箱邮件列表
params = {
    "account_id": 1,
    "folder": "INBOX",
    "limit": 20,
    "unread_only": True
}
response = requests.get(f"{API_URL}/list", params=params, headers=headers)
emails = response.json()["data"]["items"]

for email in emails:
    print(f"[{email['id']}] {email['subject']} - {email['sender']}")

# 获取邮件详情
email_id = emails[0]["id"]
detail = requests.get(
    f"{API_URL}/{email_id}",
    params={"account_id": 1},
    headers=headers
).json()
print(detail["data"]["body"])

# 标记已读
requests.put(
    f"{API_URL}/{email_id}/read",
    params={"account_id": 1, "is_read": True},
    headers=headers
)`

// cURL 接收示例
const curlReceiveCode = `# 获取邮件列表
curl -k "https://your-server/api/v1/exchange/emails/list?account_id=1&limit=10" \\
     -H "X-API-KEY: your_api_key_here"

# 获取邮件详情
curl -k "https://your-server/api/v1/exchange/emails/{email_id}?account_id=1" \\
     -H "X-API-KEY: your_api_key_here"

# 标记为已读
curl -k -X PUT "https://your-server/api/v1/exchange/emails/{email_id}/read?account_id=1&is_read=true" \\
     -H "X-API-KEY: your_api_key_here"`

// Python 同步示例
const pythonSyncCode = `import requests
import json

API_URL = "https://your-server/api/v1/exchange/emails/sync"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# 1. 首次同步（sync_state 为空）
data = {
    "account_id": 1,
    "folder": "INBOX",
    "sync_state": None,
    "limit": 100
}

response = requests.post(API_URL, json=data, headers=headers)
result = response.json()

if result['success']:
    # 保存新的 sync_state 供下次使用
    new_sync_state = result['data']['sync_state']
    print(f"Initial Sync State: {new_sync_state}")
    
    # 处理首次同步的所有邮件（change_type=create）
    for item in result['data']['items']:
        if item['change_type'] == 'create':
             print(f"[NEW] {item['item']['subject']}")
else:
    print("Sync failed")

# 2. 后续增量同步
data['sync_state'] = new_sync_state
response = requests.post(API_URL, json=data, headers=headers)
result = response.json()

if result['success']:
    new_sync_state = result['data']['sync_state'] # 更新 state
    
    for item in result['data']['items']:
        if item['change_type'] == 'create':
            print(f"[NEW EMAIL] {item['item']['subject']}")
        elif item['change_type'] == 'delete':
            print(f"[DELETED] ID: {item['id']}")
        elif item['change_type'] == 'update':
            print(f"[UPDATED] {item['item']['subject']}")
`

// cURL 同步示例
const curlSyncCode = `curl -k -X POST "https://your-server/api/v1/exchange/emails/sync" \\
     -H "X-API-KEY: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
           "account_id": 1,
           "folder": "INBOX",
           "sync_state": "YOUR_SYNC_STATE_STRING"
         }'`

// 草稿参数
const draftParams = [
  { name: 'account_id', type: 'int', required: true, desc: '账户ID' },
  { name: 'to', type: 'string[]', required: false, desc: '收件人邮箱列表' },
  { name: 'subject', type: 'string', required: false, desc: '邮件主题' },
  { name: 'body', type: 'string', required: false, desc: '邮件正文' },
  { name: 'body_type', type: 'string', required: false, desc: '"text" 或 "html"，默认 "html"' },
  { name: 'cc', type: 'string[]', required: false, desc: '抄送列表' },
  { name: 'bcc', type: 'string[]', required: false, desc: '密送列表' },
  { name: 'attachments', type: 'array', required: false, desc: '附件列表' },
]

// 回复参数
const replyParams = [
  { name: 'account_id', type: 'int', required: true, desc: '账户ID' },
  { name: 'reference_item_id', type: 'string', required: true, desc: '原邮件ID' },
  { name: 'to', type: 'string[]', required: false, desc: '收件人（不填默认回给发送者）' },
  { name: 'subject', type: 'string', required: false, desc: '邮件主题（不填自动加 Re:）' },
  { name: 'body', type: 'string', required: true, desc: '回复内容' },
  { name: 'reply_all', type: 'boolean', required: false, desc: '是否回复所有人，默认 false' },
  { name: 'cc', type: 'string[]', required: false, desc: '抄送列表' },
  { name: 'bcc', type: 'string[]', required: false, desc: '密送列表' },
  { name: 'attachments', type: 'array', required: false, desc: '附件列表' },
]

// 转发参数
const forwardParams = [
  { name: 'account_id', type: 'int', required: true, desc: '账户ID' },
  { name: 'reference_item_id', type: 'string', required: true, desc: '原邮件ID' },
  { name: 'to', type: 'string[]', required: true, desc: '收件人邮箱列表' },
  { name: 'subject', type: 'string', required: false, desc: '邮件主题（不填自动加 Fwd:）' },
  { name: 'body', type: 'string', required: false, desc: '转发附言' },
  { name: 'cc', type: 'string[]', required: false, desc: '抄送列表' },
  { name: 'bcc', type: 'string[]', required: false, desc: '密送列表' },
  { name: 'attachments', type: 'array', required: false, desc: '附件列表' },
]

// 通讯录参数
const contactParams = [
  { name: 'q', type: 'string', required: true, desc: '查询关键词 (姓名/邮箱)' },
  { name: 'account_id', type: 'int', required: true, desc: '使用的账户ID' },
]

// Python 创建草稿示例
const pythonDraftCode = `import requests

API_URL = "https://your-server/api/v1/exchange/emails/drafts"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

data = {
    "account_id": 1,
    "to": ["recipient@example.com"],
    "subject": "草稿邮件",
    "body": "<p>这是一封草稿</p>",
    "body_type": "html"
}

response = requests.post(API_URL, json=data, headers=headers)
print(response.json())`

// cURL 创建草稿示例
const curlDraftCode = `curl -k -X POST "https://your-server/api/v1/exchange/emails/drafts" \\
     -H "X-API-KEY: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
           "account_id": 1,
           "to": ["recipient@example.com"],
           "subject": "草稿邮件",
           "body": "<p>这是一封草稿</p>"
         }'

// 回复邮件示例
const pythonReplyCode = \`import requests

API_URL = "https://your-server/api/v1/exchange/emails/reply"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

data = {
    "account_id": 1,
    "reference_item_id": "AAMkAD...",
    "body": "收到，谢谢！",
    "reply_all": False
}

response = requests.post(API_URL, json=data, headers=headers)
print(response.json())\`

const curlReplyCode = \`curl -k -X POST "https://your-server/api/v1/exchange/emails/reply" \\\\
     -H "X-API-KEY: your_api_key_here" \\\\
     -H "Content-Type: application/json" \\\\
     -d '{
           "account_id": 1,
           "reference_item_id": "AAMkAD...",
           "body": "收到，谢谢！",
           "reply_all": false
         }'\`

// 转发邮件示例
const pythonForwardCode = \`import requests

API_URL = "https://your-server/api/v1/exchange/emails/forward"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

data = {
    "account_id": 1,
    "reference_item_id": "AAMkAD...",
    "to": ["forward@example.com"],
    "body": "请查收转发邮件"
}

response = requests.post(API_URL, json=data, headers=headers)
print(response.json())\`

const curlForwardCode = \`curl -k -X POST "https://your-server/api/v1/exchange/emails/forward" \\\\
     -H "X-API-KEY: your_api_key_here" \\\\
     -H "Content-Type: application/json" \\\\
     -d '{
           "account_id": 1,
           "reference_item_id": "AAMkAD...",
           "to": ["forward@example.com"],
           "body": "请查收转发邮件"
         }'\``

// 搜索示例
const pythonSearchCode = `import requests
from datetime import datetime, timedelta

API_URL = "https://your-server/api/v1/exchange/emails/search"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# 搜索最近7天包含"报告"的邮件
data = {
    "account_id": 1,
    "query": "报告",
    "folder": "INBOX",
    "date_from": (datetime.now() - timedelta(days=7)).isoformat(),
    "limit": 50
}

response = requests.post(API_URL, json=data, headers=headers)
results = response.json()["data"]["items"]

for email in results:
    print(f"{email['received_time']} - {email['subject']}")`

// 模板发送示例 - Python
const pythonTemplateCode = `import requests

API_URL = "https://your-server/api/v1/exchange/emails/send-template"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# 使用模板发送邮件
data = {
    "template_id": 1,           # 模板ID
    "account_id": 1,            # 发送账户
    "to": ["user@example.com"],
    "variables": {              # 变量替换
        "name": "张经理",
        "file_name": "《品牌宣传指南 v2.0》"
    },
    "cc": ["manager@example.com"]
}

response = requests.post(API_URL, json=data, headers=headers)
result = response.json()

if result.get("code") == 200:
    print(f"发送成功，日志ID: {result['data']['log_id']}")
    print(f"使用模板: {result['data']['template_id']}")
else:
    print(f"发送失败: {result.get('msg')}")`

// 模板发送示例 - cURL
const curlTemplateCode = `curl -k -X POST "https://your-server/api/v1/exchange/emails/send-template" \\
     -H "X-API-KEY: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
           "template_id": 1,
           "account_id": 1,
           "to": ["user@example.com"],
           "variables": {
             "name": "张经理",
             "file_name": "《品牌宣传指南 v2.0》"
           }
         }'`

// 通讯录结果示例
const contactResponseCode = `{
  "success": true,
  "data": [
    {
      "name": "张阳阳(Maggie)",       // 显示名称
      "email": "maggie.zhang@example.com", // 邮箱
      "mailbox_type": "Contact",      // 类型
      "item_id": "AAMkAGQ..."         // ID
    }
  ]
}`

// 通讯录 - Python
const pythonContactCode = `import requests

API_URL = "https://your-server/api/v1/exchange/contacts/resolve"
API_KEY = "your_api_key_here"
headers = {"X-API-KEY": API_KEY}

params = {
    "q": "Maggie",
    "account_id": 1
}

response = requests.get(API_URL, params=params, headers=headers)
print(response.json())`

// 通讯录 - cURL
const curlContactCode = `curl -k -G "https://your-server/api/v1/exchange/contacts/resolve" \\
    -H "X-API-KEY: your_api_key_here" \\
    -d "q=Maggie" \\
    -d "account_id=1"`

// Webhook Payload
const webhookPayloadCode = `{
  "event_type": "NewMail",
  "account_id": 1,
  "item_id": "AAMkAGQ...",
  "subject": "测试邮件",
  "sender": "sender@example.com",
  "received_time": "2023-10-27T10:00:00",
  "folder_id": "..."
}`

// Webhook 验签示例
const pythonWebhookVerifyCode = `import hmac
import hashlib
import json
from fastapi import Request, HTTPException

WEBHOOK_SECRET = "your_webhook_secret_here"

async def webhook_endpoint(request: Request):
    # 1. 获取签名
    signature = request.headers.get("X-Exchange-Signature")
    if not signature:
        raise HTTPException(400, "Missing signature")
        
    # 2. 获取原始请求体 (bytes)
    body_bytes = await request.body()
    
    # 3. 计算签名
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body_bytes,        # 注意：必须使用原始请求体字节流
        hashlib.sha256
    ).hexdigest()
    
    # 4. 对比签名
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(403, "Invalid signature")
        
    # 5. 处理业务逻辑
    payload = json.loads(body_bytes)
    print(f"收到新邮件: {payload['subject']}")
    
    return {"status": "ok"}
`
</script>
