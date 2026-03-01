<script setup>
import { h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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

defineOptions({ name: 'ApiKeyManagement' })

const { t } = useI18n()

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
  name: t('exchange.keys.name'),
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
        $message.success(t('exchange.keys.create_success'))
        if (res.data?.api_key) {
          newApiKey.value = res.data.api_key
          showKeyModal.value = true
        }
        modalVisible.value = false
        $table.value?.handleSearch()
      } else {
        $message.error(res.msg || t('exchange.keys.create_fail'))
      }
    } catch (err) {
      $message.error(t('exchange.keys.create_fail') + ': ' + err.message)
    }
  })
}

// 撤销密钥
async function handleRevoke(row) {
  try {
    const res = await api.revokeExchangeApiKey({ key_id: row.id })
    if (res.code === 200) {
      $message.success(t('exchange.keys.revoke_success'))
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || t('exchange.keys.revoke_fail'))
    }
  } catch (err) {
    $message.error(t('exchange.keys.revoke_fail') + ': ' + err.message)
  }
}

// 删除密钥
async function handleDelete(row) {
  try {
    const res = await api.deleteExchangeApiKey({ key_id: row.id })
    if (res.code === 200) {
      $message.success(t('exchange.keys.delete_success'))
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || t('exchange.keys.delete_fail'))
    }
  } catch (err) {
    $message.error(t('exchange.keys.delete_fail') + ': ' + err.message)
  }
}

// 复制密钥
async function copyKey() {
  const text = newApiKey.value
  if (!text) {
    $message.error(t('exchange.keys.copy_nothing'))
    return
  }
  
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      $message.success(t('exchange.keys.copy_success'))
      return
    } catch (err) {
      console.error('[copyKey] Clipboard API 失败:', err)
    }
  }
  
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
    $message.success(t('exchange.keys.copy_success'))
  } else {
    $message.warning(t('exchange.keys.copy_fail'))
  }
}

onMounted(() => {
  $table.value?.handleSearch()
  loadAccounts()
})

const permissionOptions = [
  { label: () => t('exchange.keys.perm_send'), value: 'send' },
  { label: () => t('exchange.keys.perm_drafts'), value: 'drafts' },
  { label: () => t('exchange.keys.perm_receive'), value: 'receive' },
  { label: () => t('exchange.keys.perm_search'), value: 'search' },
  { label: () => t('exchange.keys.perm_delete'), value: 'delete' },
  { label: () => t('exchange.keys.perm_folders'), value: 'folders' },
  { label: () => t('exchange.keys.perm_sync'), value: 'sync' },
  { label: () => t('exchange.keys.perm_read'), value: 'read' },
  { label: () => t('exchange.keys.perm_reply'), value: 'reply' },
  { label: () => t('exchange.keys.perm_forward'), value: 'forward' },
  { label: () => t('exchange.keys.perm_contacts'), value: 'contacts' },
]

const columns = [
  {
    title: () => t('exchange.keys.col_name'),
    key: 'name',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.keys.col_prefix'),
    key: 'key_prefix',
    width: 100,
    align: 'center',
    render(row) {
      return h(NCode, {}, { default: () => row.key_prefix + '...' })
    },
  },
  {
    title: () => t('exchange.keys.col_permissions'),
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
    title: () => t('exchange.keys.col_status'),
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      const expired = row.expires_at && new Date(row.expires_at) < new Date()
      if (expired) {
        return h(NTag, { type: 'error' }, { default: () => t('exchange.keys.status_expired') })
      }
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'warning' },
        { default: () => (row.is_active ? t('exchange.keys.status_active') : t('exchange.keys.status_revoked')) }
      )
    },
  },
  {
    title: () => t('exchange.keys.col_rate_limit'),
    key: 'rate_limit',
    width: 100,
    align: 'center',
    render(row) {
      return `${row.rate_limit}${t('exchange.keys.rate_per_minute')}`
    },
  },
  {
    title: () => t('exchange.keys.col_usage'),
    key: 'usage_count',
    width: 100,
    align: 'center',
  },
  {
    title: () => t('exchange.keys.col_last_used'),
    key: 'last_used_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.last_used_at ? formatDate(row.last_used_at) : '-'
    },
  },
  {
    title: () => t('exchange.keys.col_expires'),
    key: 'expires_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.expires_at ? formatDate(row.expires_at) : t('exchange.keys.never_expires')
    },
  },
  {
    title: () => t('exchange.keys.col_actions'),
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
                    default: () => t('exchange.keys.btn_revoke'),
                    icon: renderIcon('mdi:cancel', { size: 16 }),
                  }
                ),
              default: () => t('exchange.keys.confirm_revoke'),
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
                  default: () => t('exchange.keys.btn_delete'),
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => t('exchange.keys.confirm_delete'),
          }
        ),
      ]
    },
  },
]

const validateForm = {
  name: [{ required: true, message: () => t('exchange.keys.validate_name_required'), trigger: ['input', 'blur'] }],
  permissions: [
    { type: 'array', required: true, message: () => t('exchange.keys.validate_permissions_required'), trigger: ['change'] },
  ],
}
</script>

<template>
  <CommonPage show-footer :title="$t('exchange.keys.title')">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('exchange.keys.add') }}
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
        <NFormItem :label="$t('exchange.keys.form_name')" path="name">
          <NInput v-model:value="modalForm.name" clearable :placeholder="$t('exchange.keys.placeholder_name')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_permissions')" path="permissions">
          <NSelect
            v-model:value="modalForm.permissions"
            multiple
            :options="permissionOptions"
            :placeholder="$t('exchange.keys.placeholder_permissions')"
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_rate_limit')" path="rate_limit">
          <NInputNumber
            v-model:value="modalForm.rate_limit"
            :min="1"
            :max="10000"
            :placeholder="$t('exchange.keys.placeholder_rate_limit')"
          />
          <span style="margin-left: 8px; color: #999">{{ $t('exchange.keys.unit_per_minute') }}</span>
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_expires_days')" path="expires_days">
          <NInputNumber
            v-model:value="modalForm.expires_days"
            :min="1"
            :max="3650"
            :placeholder="$t('exchange.keys.placeholder_expires_days')"
          />
          <span style="margin-left: 8px; color: #999">{{ $t('exchange.keys.unit_days') }}</span>
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_allowed_accounts')" path="allowed_accounts">
          <NSelect
            v-model:value="modalForm.allowed_accounts"
            multiple
            :options="accountOptions"
            :placeholder="$t('exchange.keys.placeholder_allowed_accounts')"
            clearable
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_ip_whitelist')" path="ip_whitelist">
          <NInput
            v-model:value="modalForm.ip_whitelist_str"
            type="textarea"
            :placeholder="$t('exchange.keys.placeholder_ip_whitelist')"
            :autosize="{ minRows: 2, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.keys.form_remark')" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable :placeholder="$t('exchange.keys.placeholder_remark')" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 密钥显示弹窗 -->
    <CrudModal
      v-model:visible="showKeyModal"
      :title="$t('exchange.keys.key_created_title')"
      :show-footer="false"
      style="width: 600px; max-width: 90vw"
    >
      <NAlert type="warning" :title="$t('exchange.keys.key_created_warning')" style="margin-bottom: 16px">
        {{ $t('exchange.keys.key_created_message') }}
      </NAlert>
      <div style="background: #f5f5f5; padding: 16px; border-radius: 4px; margin-bottom: 16px; overflow: hidden">
        <code style="display: block; word-break: break-all; overflow-wrap: break-word; white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #333; line-height: 1.5">{{ newApiKey }}</code>
      </div>
      <NButton type="primary" block @click="copyKey">
        <TheIcon icon="mdi:content-copy" :size="18" class="mr-5" />{{ $t('exchange.keys.btn_copy_key') }}
      </NButton>
    </CrudModal>
  </CommonPage>
</template>
