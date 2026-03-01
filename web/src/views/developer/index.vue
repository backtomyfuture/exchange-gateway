<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <n-card :title="$t('developer.title')" size="small" rounded-10 segmented>
        <template #header-extra>
            <n-button tag="a" href="/docs" target="_blank" type="primary" dashed>
                {{ $t('developer.open_swagger') }}
            </n-button>
        </template>
        
        <n-alert :title="$t('developer.about_title')" type="info" mb-20>
           {{ $t('developer.about_desc') }}<br/>
           {{ $t('developer.about_note') }}
        </n-alert>

        <n-tabs type="line" animated>
          <!-- 1. 认证 -->
          <n-tab-pane name="auth" :tab="$t('developer.tab_auth')">
            <n-space vertical>
                <div class="text-16 font-bold">{{ $t('developer.get_api_key') }}</div>
                <ol class="pl-20">
                    <li>{{ $t('developer.auth_step_1') }} <n-tag type="success">{{ $t('developer.auth_step_1_menu1') }}</n-tag> -> <n-tag type="success">{{ $t('developer.auth_step_1_menu2') }}</n-tag> {{ $t('developer.auth_step_1_suffix') }}</li>
                    <li>{{ $t('developer.auth_step_2') }}</li>
                    <li>{{ $t('developer.auth_step_3') }} <n-tag type="warning">{{ $t('developer.auth_step_3_warning') }}</n-tag></li>
                </ol>

                <div class="text-16 font-bold mt-20">{{ $t('developer.request_header') }}</div>
                <n-code language="http" :code="authHeaderCode" />

                <n-alert type="warning" :title="$t('developer.security_tip_title')" class="mt-16">
                  <ul class="pl-20 mb-0">
                    <li>{{ $t('developer.security_tip_1') }}</li>
                    <li>{{ $t('developer.security_tip_2') }}</li>
                    <li>{{ $t('developer.security_tip_3') }}</li>
                  </ul>
                </n-alert>
            </n-space>
          </n-tab-pane>

          <!-- 2. 发送邮件 -->
          <n-tab-pane name="send" :tab="$t('developer.tab_send')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/send</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">send</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.send_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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
          <n-tab-pane name="receive" :tab="$t('developer.tab_receive')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_list')">GET /api/v1/exchange/emails/list</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_detail')">GET /api/v1/exchange/emails/{email_id}</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_mark')">PUT /api/v1/exchange/emails/{email_id}/read</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">{{ $t('developer.label_permission_receive') }}</n-descriptions-item>
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

          <!-- 3.6. 文件夹管理 -->
          <n-tab-pane name="folders" :tab="$t('developer.tab_folders')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">GET /api/v1/exchange/emails/folders/all</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">folders</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.folders_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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

          <!-- 3.5. 邮件同步 -->
          <n-tab-pane name="sync" :tab="$t('developer.tab_sync')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/sync</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">sync</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.sync_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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

          <!-- 3.8. 创建草稿 -->
          <n-tab-pane name="drafts" :tab="$t('developer.tab_drafts')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/drafts</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">drafts</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.drafts_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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

          <!-- 3.9. 回复邮件 -->
          <n-tab-pane name="reply" :tab="$t('developer.tab_reply')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/reply</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">reply</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.reply_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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

          <!-- 3.10. 转发邮件 -->
          <n-tab-pane name="forward" :tab="$t('developer.tab_forward')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/forward</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">forward</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.forward_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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
          <n-tab-pane name="search" :tab="$t('developer.tab_search')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/search</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">search</n-descriptions-item>
            </n-descriptions>
            
            <n-code language="python" :code="pythonSearchCode" />
          </n-tab-pane>
          
          <!-- 5. 模板发送 -->
          <n-tab-pane name="template" :tab="$t('developer.tab_template')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">POST /api/v1/exchange/emails/send-template</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">send</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_variable_syntax')"><code>{{ variableSyntaxExample }}</code></n-descriptions-item>
            </n-descriptions>

            <n-alert type="info" :title="$t('developer.template_desc_title')" class="mb-16">
              <ul class="pl-20 mb-0">
                <li>{{ $t('developer.template_desc_1') }}</li>
                <li>{{ $t('developer.template_desc_2') }}</li>
                <li>{{ $t('developer.template_desc_3') }}</li>
              </ul>
            </n-alert>

            <div class="text-14 font-bold mb-8">{{ $t('developer.request_params') }}</div>
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
          <n-tab-pane name="contacts" :tab="$t('developer.tab_contacts')">
            <n-descriptions :column="1" label-placement="left" bordered mb-16>
              <n-descriptions-item :label="$t('developer.label_endpoint')">GET /api/v1/exchange/contacts/resolve</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_permission')">contacts</n-descriptions-item>
              <n-descriptions-item :label="$t('developer.label_description')">{{ $t('developer.contact_resolve_desc') }}</n-descriptions-item>
            </n-descriptions>

            <div class="text-14 font-bold mb-8">{{ $t('developer.query_params') }}</div>
            <n-data-table :columns="sendParamColumns" :data="contactParams" :bordered="false" size="small" class="mb-16" />
            
            <div class="text-14 font-bold mb-8">{{ $t('developer.response_structure') }}</div>
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
          <n-tab-pane name="webhook" :tab="$t('developer.tab_webhook')">
            <n-alert type="info" :title="$t('developer.webhook_desc_title')" class="mb-16">
              <ul class="pl-20 mb-0">
                <li>{{ $t('developer.webhook_desc_1') }}</li>
                <li>{{ $t('developer.webhook_desc_2') }}</li>
                <li>{{ $t('developer.webhook_desc_3') }}</li>
              </ul>
            </n-alert>

            <div class="text-14 font-bold mb-8">{{ $t('developer.webhook_payload') }}</div>
            <n-code language="json" :code="webhookPayloadCode" class="mb-16" />

            <div class="text-14 font-bold mb-8">{{ $t('developer.webhook_verify') }}</div>
            <n-code language="python" :code="pythonWebhookVerifyCode" />
          </n-tab-pane>

          <!-- 8. 错误处理 -->
           <n-tab-pane name="errors" :tab="$t('developer.tab_errors')">
             <n-data-table :columns="errorColumns" :data="errorCodes" :bordered="false" size="small" />
           </n-tab-pane>
        </n-tabs>
      </n-card>
    </div>
  </AppPage>
</template>

<script setup>
import { h, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { NCode, NTag, NDescriptions, NDescriptionsItem, NDataTable } from 'naive-ui'

const { t } = useI18n()

const variableSyntaxExample = computed(() =>
  `{{ ${t('developer.label_variable_name')} }}`
)

// 认证头
const authHeaderCode = `X-API-KEY: your_api_key_here`

// 发送参数表格
const sendParamColumns = [
  { title: () => t('developer.param_col_name'), key: 'name', width: 120 },
  { title: () => t('developer.param_col_type'), key: 'type', width: 100 },
  { title: () => t('developer.param_col_required'), key: 'required', width: 60,
    render: (row) => h(NTag, { type: row.required ? 'error' : 'default', size: 'small' }, 
      { default: () => row.required ? t('developer.param_yes') : t('developer.param_no') })
  },
  { title: () => t('developer.param_col_desc'), key: 'desc' },
]

const sendParams = [
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'to', type: 'string[]', required: true, desc: () => t('developer.param_to') },
  { name: 'subject', type: 'string', required: true, desc: () => t('developer.param_subject') },
  { name: 'body', type: 'string', required: true, desc: () => t('developer.param_body') },
  { name: 'body_type', type: 'string', required: false, desc: () => t('developer.param_body_type') },
  { name: 'cc', type: 'string[]', required: false, desc: () => t('developer.param_cc') },
  { name: 'bcc', type: 'string[]', required: false, desc: () => t('developer.param_bcc') },
  { name: 'attachments', type: 'array', required: false, desc: () => t('developer.param_attachments') },
]

// 同步请求参数
const syncParams = [
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'folder', type: 'string', required: false, desc: () => t('developer.sync_folder_desc') },
  { name: 'sync_state', type: 'string', required: false, desc: () => t('developer.sync_state_desc') },
  { name: 'limit', type: 'int', required: false, desc: () => t('developer.sync_limit_desc') },
  { name: 'only_fields', type: 'string[]', required: false, desc: () => t('developer.sync_only_fields_desc') },
]

// 文件夹参数
const folderParams = [
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
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
  { title: () => t('developer.error_col_code'), key: 'code', width: 100,
    render: (row) => h(NTag, { type: row.type, size: 'small' }, { default: () => row.code })
  },
  { title: () => t('developer.error_col_desc'), key: 'desc' },
  { title: () => t('developer.error_col_action'), key: 'action' },
]

const errorCodes = [
  { code: '200', type: 'success', desc: () => t('developer.error_200'), action: () => t('developer.error_200_action') },
  { code: '401', type: 'error', desc: () => t('developer.error_401'), action: () => t('developer.error_401_action') },
  { code: '403', type: 'error', desc: () => t('developer.error_403'), action: () => t('developer.error_403_action') },
  { code: '404', type: 'warning', desc: () => t('developer.error_404'), action: () => t('developer.error_404_action') },
  { code: '422', type: 'warning', desc: () => t('developer.error_422'), action: () => t('developer.error_422_action') },
  { code: '429', type: 'warning', desc: () => t('developer.error_429'), action: () => t('developer.error_429_action') },
  { code: '500', type: 'error', desc: () => t('developer.error_500'), action: () => t('developer.error_500_action') },
]

// 模板发送参数
const templateParams = [
  { name: 'template_id', type: 'int', required: true, desc: () => t('developer.template_param_id') },
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'to', type: 'string[]', required: true, desc: () => t('developer.param_to') },
  { name: 'variables', type: 'object', required: false, desc: () => t('developer.template_param_vars') },
  { name: 'cc', type: 'string[]', required: false, desc: () => t('developer.param_cc') },
  { name: 'bcc', type: 'string[]', required: false, desc: () => t('developer.param_bcc') },
  { name: 'attachments', type: 'array', required: false, desc: t('developer.param_attachments_short') },
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
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'to', type: 'string[]', required: false, desc: () => t('developer.param_to') },
  { name: 'subject', type: 'string', required: false, desc: () => t('developer.param_subject') },
  { name: 'body', type: 'string', required: false, desc: () => t('developer.param_body') },
  { name: 'body_type', type: 'string', required: false, desc: () => t('developer.drafts_body_type_desc') },
  { name: 'cc', type: 'string[]', required: false, desc: () => t('developer.param_cc') },
  { name: 'bcc', type: 'string[]', required: false, desc: () => t('developer.param_bcc') },
  { name: 'attachments', type: 'array', required: false, desc: t('developer.param_attachments_short') },
]

// 回复参数
const replyParams = [
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'reference_item_id', type: 'string', required: true, desc: () => t('developer.reply_ref_desc') },
  { name: 'to', type: 'string[]', required: false, desc: () => t('developer.reply_to_desc') },
  { name: 'subject', type: 'string', required: false, desc: () => t('developer.reply_subject_desc') },
  { name: 'body', type: 'string', required: true, desc: () => t('developer.reply_body_desc') },
  { name: 'reply_all', type: 'boolean', required: false, desc: () => t('developer.reply_all_desc') },
  { name: 'cc', type: 'string[]', required: false, desc: () => t('developer.param_cc') },
  { name: 'bcc', type: 'string[]', required: false, desc: () => t('developer.param_bcc') },
  { name: 'attachments', type: 'array', required: false, desc: t('developer.param_attachments_short') },
]

// 转发参数
const forwardParams = [
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.param_account_id') },
  { name: 'reference_item_id', type: 'string', required: true, desc: () => t('developer.reply_ref_desc') },
  { name: 'to', type: 'string[]', required: true, desc: () => t('developer.param_to') },
  { name: 'subject', type: 'string', required: false, desc: () => t('developer.forward_subject_desc') },
  { name: 'body', type: 'string', required: false, desc: () => t('developer.forward_body_desc') },
  { name: 'cc', type: 'string[]', required: false, desc: () => t('developer.param_cc') },
  { name: 'bcc', type: 'string[]', required: false, desc: () => t('developer.param_bcc') },
  { name: 'attachments', type: 'array', required: false, desc: t('developer.param_attachments_short') },
]

// 通讯录参数
const contactParams = [
  { name: 'q', type: 'string', required: true, desc: () => t('developer.contact_q_desc') },
  { name: 'account_id', type: 'int', required: true, desc: () => t('developer.contact_account_desc') },
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
