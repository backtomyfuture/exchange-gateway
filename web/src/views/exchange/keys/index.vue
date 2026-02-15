<script setup>
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSpace,
  NTag,
  NPopconfirm,
  NSelect,
  NAlert,
  NText,
  NCode,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: 'API密钥管理' })

const $table = ref(null)
const queryItems = ref({})

// 新创建的密钥（仅显示一次）
const newApiKey = ref('')
const showKeyModal = ref(false)

// 账户选项列表
const accountOptions = ref([])

// 加载账户列表
async function loadAccounts() {
  try {
    const res = await api.getExchangeAccounts({ page_size: 100 })
    if (res.code === 200) {
      accountOptions.value = (res.data || []).map(acc => ({
        label: `${acc.email} (ID: ${acc.id})`,
        value: acc.id,
      }))
    }
  } catch (err) {
    console.error('加载账户失败', err)
  }
}

const {
  modalVisible,
  modalTitle,
  modalAction,
  modalLoading,
  modalForm,
  modalFormRef,
  handleAdd,
} = useCRUD({
  name: 'API密钥',
  initForm: {
    permissions: ['send', 'drafts', 'receive', 'search', 'delete', 'folders', 'sync', 'read', 'reply', 'forward', 'contacts'],
    rate_limit: 100,
    expires_days: 365,
    allowed_accounts: [],
    ip_whitelist: [],
  },
  doCreate: async (data) => {
    const res = await api.createExchangeApiKey(data)
    if (res.code === 200 && res.data?.api_key) {
      newApiKey.value = res.data.api_key
      showKeyModal.value = true
    }
    return res
  },
  doUpdate: () => {},
  doDelete: api.deleteExchangeApiKey,
  refresh: () => $table.value?.handleSearch(),
})

// 保存密钥
async function handleSaveKey() {
  modalFormRef.value?.validate(async (errors) => {
    if (errors) return
    try {
      const res = await api.createExchangeApiKey(modalForm.value)
      if (res.code === 200) {
        $message.success('创建成功')
        if (res.data?.api_key) {
          newApiKey.value = res.data.api_key
          showKeyModal.value = true
        }
        modalVisible.value = false
        $table.value?.handleSearch()
      } else {
        $message.error(res.msg || '创建失败')
      }
    } catch (err) {
      $message.error('创建失败: ' + err.message)
    }
  })
}

// 撤销密钥
async function handleRevoke(row) {
  try {
    const res = await api.revokeExchangeApiKey({ key_id: row.id })
    if (res.code === 200) {
      $message.success('撤销成功')
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || '撤销失败')
    }
  } catch (err) {
    $message.error('撤销失败: ' + err.message)
  }
}

// 删除密钥
async function handleDelete(row) {
  try {
    const res = await api.deleteExchangeApiKey({ key_id: row.id })
    if (res.code === 200) {
      $message.success('删除成功')
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || '删除失败')
    }
  } catch (err) {
    $message.error('删除失败: ' + err.message)
  }
}

// 复制密钥
async function copyKey() {
  const text = newApiKey.value
  if (!text) {
    $message.error('没有可复制的密钥')
    return
  }
  
  // 在安全上下文中使用 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      $message.success('已复制到剪贴板')
      return
    } catch (err) {
      console.error('[copyKey] Clipboard API 失败:', err)
      // 继续尝试降级方案
    }
  }
  
  // 降级方案：使用 execCommand
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 2px;
    height: 2px;
    padding: 0;
    border: none;
    outline: none;
    box-shadow: none;
    background: transparent;
  `
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  textArea.setSelectionRange(0, text.length)
  
  let success = false
  try {
    success = document.execCommand('copy')
  } catch (err) {
    console.error('[copyKey] execCommand 异常:', err)
  }
  
  document.body.removeChild(textArea)
  
  if (success) {
    $message.success('已复制到剪贴板')
  } else {
    $message.warning('自动复制失败，请手动选择上方密钥并按 Ctrl+C 复制')
  }
}

onMounted(() => {
  $table.value?.handleSearch()
  loadAccounts()
})

const permissionOptions = [
  { label: '发送邮件', value: 'send' },
  { label: '创建草稿', value: 'drafts' },
  { label: '接收邮件', value: 'receive' },
  { label: '搜索邮件', value: 'search' },
  { label: '删除邮件', value: 'delete' },
  { label: '文件夹操作', value: 'folders' },
  { label: '邮件同步', value: 'sync' },
  { label: '标记已读', value: 'read' },
  { label: '回复邮件', value: 'reply' },
  { label: '转发邮件', value: 'forward' },
  { label: '通讯录', value: 'contacts' },
]

const columns = [
  {
    title: '名称',
    key: 'name',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: '密钥前缀',
    key: 'key_prefix',
    width: 100,
    align: 'center',
    render(row) {
      return h(NCode, {}, { default: () => row.key_prefix + '...' })
    },
  },
  {
    title: '权限',
    key: 'permissions',
    width: 200,
    render(row) {
      const perms = row.permissions || []
      return h(
        NSpace,
        { size: 'small' },
        {
          default: () =>
            perms.map((p) =>
              h(NTag, { size: 'small', type: 'info' }, { default: () => p })
            ),
        }
      )
    },
  },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      const expired = row.expires_at && new Date(row.expires_at) < new Date()
      if (expired) {
        return h(NTag, { type: 'error' }, { default: () => '已过期' })
      }
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'warning' },
        { default: () => (row.is_active ? '有效' : '已撤销') }
      )
    },
  },
  {
    title: '速率限制',
    key: 'rate_limit',
    width: 100,
    align: 'center',
    render(row) {
      return `${row.rate_limit}/分钟`
    },
  },
  {
    title: '使用次数',
    key: 'usage_count',
    width: 100,
    align: 'center',
  },
  {
    title: '最后使用',
    key: 'last_used_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.last_used_at ? formatDate(row.last_used_at) : '-'
    },
  },
  {
    title: '过期时间',
    key: 'expires_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.expires_at ? formatDate(row.expires_at) : '永不过期'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        row.is_active &&
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleRevoke(row),
            },
            {
              trigger: () =>
                h(
                  NButton,
                  { size: 'small', type: 'warning', style: 'margin-right: 8px;' },
                  {
                    default: () => '撤销',
                    icon: renderIcon('mdi:cancel', { size: 16 }),
                  }
                ),
              default: () => '确定撤销该密钥吗？撤销后将无法使用',
            }
          ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete(row),
          },
          {
            trigger: () =>
              h(
                NButton,
                { size: 'small', type: 'error' },
                {
                  default: () => '删除',
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => '确定永久删除该密钥吗？',
          }
        ),
      ]
    },
  },
]

const validateForm = {
  name: [{ required: true, message: '请输入密钥名称', trigger: ['input', 'blur'] }],
  permissions: [
    { type: 'array', required: true, message: '请至少选择一个权限', trigger: ['change'] },
  ],
}
</script>

<template>
  <CommonPage show-footer title="API密钥管理">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />创建密钥
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getExchangeApiKeys"
    />

    <!-- 新建密钥弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSaveKey"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="100"
        :model="modalForm"
        :rules="validateForm"
      >
        <NFormItem label="密钥名称" path="name">
          <NInput v-model:value="modalForm.name" clearable placeholder="用于识别密钥用途" />
        </NFormItem>
        <NFormItem label="权限" path="permissions">
          <NSelect
            v-model:value="modalForm.permissions"
            multiple
            :options="permissionOptions"
            placeholder="选择允许的操作"
          />
        </NFormItem>
        <NFormItem label="速率限制" path="rate_limit">
          <NInputNumber
            v-model:value="modalForm.rate_limit"
            :min="1"
            :max="10000"
            placeholder="每分钟请求数"
          />
          <span style="margin-left: 8px; color: #999">次/分钟</span>
        </NFormItem>
        <NFormItem label="过期天数" path="expires_days">
          <NInputNumber
            v-model:value="modalForm.expires_days"
            :min="1"
            :max="3650"
            placeholder="有效天数"
          />
          <span style="margin-left: 8px; color: #999">天</span>
        </NFormItem>
        <NFormItem label="允许账户" path="allowed_accounts">
          <NSelect
            v-model:value="modalForm.allowed_accounts"
            multiple
            :options="accountOptions"
            placeholder="留空表示允许所有账户"
            clearable
          />
        </NFormItem>
        <NFormItem label="IP白名单" path="ip_whitelist">
          <NInput
            v-model:value="modalForm.ip_whitelist_str"
            type="textarea"
            placeholder="每行一个IP，留空不限制"
            :autosize="{ minRows: 2, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem label="备注" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable placeholder="可选" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 密钥显示弹窗 -->
    <CrudModal
      v-model:visible="showKeyModal"
      title="密钥创建成功"
      :show-footer="false"
      style="width: 600px; max-width: 90vw"
    >
      <NAlert type="warning" title="请妥善保存" style="margin-bottom: 16px">
        密钥仅显示一次，关闭后将无法再次查看。请立即复制保存！
      </NAlert>
      <div style="background: #f5f5f5; padding: 16px; border-radius: 4px; margin-bottom: 16px; overflow: hidden">
        <code style="display: block; word-break: break-all; overflow-wrap: break-word; white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #333; line-height: 1.5">{{ newApiKey }}</code>
      </div>
      <NButton type="primary" block @click="copyKey">
        <TheIcon icon="mdi:content-copy" :size="18" class="mr-5" />复制密钥
      </NButton>
    </CrudModal>
  </CommonPage>
</template>
