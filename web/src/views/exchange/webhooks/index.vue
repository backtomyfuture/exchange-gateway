<script setup>
import { h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NSpace,
  NTag,
  NPopconfirm,
  NSelect,
  NAlert,
  NText,
  NSwitch,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: 'Webhook订阅管理' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})

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
  handleEdit,
  handleSave,
} = useCRUD({
  name: 'Webhook订阅',
  initForm: {
    account_id: null,
    url: '',
    events: ['NewMailEvent'],
    remark: '',
    is_active: true,
    secret: '',
  },
  doCreate: api.createWebhook,
  doUpdate: async (data) => {
    const updateData = { ...data }
    if (!updateData.secret) {
      delete updateData.secret
    }
    return api.updateWebhook(data.id, updateData)
  },
  doDelete: ({ id }) => api.deleteWebhook(id),
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
  loadAccounts()
})

// 事件类型选项
const eventOptions = [
  { label: () => t('exchange.webhooks.event_new_mail'), value: 'NewMailEvent' },
  { label: () => t('exchange.webhooks.event_created'), value: 'CreatedEvent' },
  { label: () => t('exchange.webhooks.event_modified'), value: 'ModifiedEvent' },
  { label: () => t('exchange.webhooks.event_deleted'), value: 'DeletedEvent' },
  { label: () => t('exchange.webhooks.event_moved'), value: 'MovedEvent' },
  { label: () => t('exchange.webhooks.event_copied'), value: 'CopiedEvent' },
  { label: () => t('exchange.webhooks.event_freebusy'), value: 'FreeBusyChangedEvent' },
]

const columns = [
  {
    title: 'ID',
    key: 'id',
    width: 70,
    align: 'center',
  },
  {
    title: () => t('exchange.webhooks.col_callback_url'),
    key: 'url',
    width: 250,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.webhooks.col_account'),
    key: 'account_id',
    width: 120,
    render(row) {
      const acc = accountOptions.value.find(a => a.value === row.account_id)
      return acc ? acc.label : `ID: ${row.account_id}`
    },
  },
  {
    title: () => t('exchange.webhooks.col_events'),
    key: 'events',
    width: 200,
    render(row) {
      const events = row.events || []
      return h(
        NSpace,
        { size: 'small' },
        {
          default: () =>
            events.slice(0, 3).map((e) =>
              h(NTag, { size: 'small', type: 'info' }, { default: () => e })
            ),
        }
      )
    },
  },
  {
    title: () => t('exchange.webhooks.col_status'),
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'default' },
        { default: () => (row.is_active ? t('exchange.webhooks.status_active') : t('exchange.webhooks.status_inactive')) }
      )
    },
  },
  {
    title: () => t('exchange.webhooks.col_remark'),
    key: 'remark',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.webhooks.col_created_at'),
    key: 'created_at',
    width: 160,
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: () => t('exchange.webhooks.col_actions'),
    key: 'actions',
    width: 180,
    align: 'center',
    fixed: 'right',
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: () => handleTest(row),
            },
            {
              default: () => t('exchange.webhooks.btn_test'),
              icon: renderIcon('mdi:send', { size: 14 }),
            }
          ),
          h(
            NButton,
            {
              size: 'small',
              onClick: () => handleEdit(row),
            },
            {
              default: () => t('exchange.webhooks.btn_edit'),
              icon: renderIcon('mdi:pencil', { size: 14 }),
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
                    default: () => t('exchange.webhooks.btn_delete'),
                    icon: renderIcon('material-symbols:delete-outline', { size: 14 }),
                  }
                ),
              default: () => t('exchange.webhooks.confirm_delete'),
            }
          ),
        ],
      })
    },
  },
]

// 测试 Webhook
async function handleTest(row) {
  try {
    const res = await api.testWebhook(row.id)
    if (res.code === 200) {
      $message.success(t('exchange.webhooks.test_success'))
    } else {
      $message.error(res.msg || t('exchange.webhooks.test_fail'))
    }
  } catch (err) {
    $message.error(t('exchange.webhooks.test_fail') + ': ' + err.message)
  }
}

// 删除
async function handleDelete(row) {
  try {
    const res = await api.deleteWebhook(row.id)
    if (res.code === 200) {
      $message.success(t('exchange.webhooks.delete_success'))
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || t('exchange.webhooks.delete_fail'))
    }
  } catch (err) {
    $message.error(t('exchange.webhooks.delete_fail') + ': ' + err.message)
  }
}

const validateForm = {
  account_id: [{ required: true, message: () => t('exchange.webhooks.validate_account_required'), trigger: 'change', type: 'number' }],
  url: [{ required: true, message: () => t('exchange.webhooks.validate_url_required'), trigger: 'input' }],
  events: [{ type: 'array', required: true, message: () => t('exchange.webhooks.validate_events_required'), trigger: 'change' }],
  secret: [
    { required: true, message: () => t('exchange.webhooks.validate_secret_required'), trigger: 'input' },
    { min: 8, message: () => t('exchange.webhooks.validate_secret_min'), trigger: 'input' },
  ],
}
</script>

<template>
  <CommonPage show-footer :title="$t('exchange.webhooks.title')">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('exchange.webhooks.add') }}
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getWebhooks"
    />

    <!-- 新建/编辑弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="100"
        :model="modalForm"
        :rules="validateForm"
      >
        <NFormItem :label="$t('exchange.webhooks.form_account')" path="account_id">
          <NSelect
            v-model:value="modalForm.account_id"
            :options="accountOptions"
            :placeholder="$t('exchange.webhooks.placeholder_account')"
            clearable
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.webhooks.form_url')" path="url">
          <NInput
            v-model:value="modalForm.url"
            :placeholder="$t('exchange.webhooks.placeholder_url')"
            clearable
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.webhooks.form_events')" path="events">
          <NSelect
            v-model:value="modalForm.events"
            multiple
            :options="eventOptions"
            :placeholder="$t('exchange.webhooks.placeholder_events')"
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.webhooks.form_secret')" path="secret">
          <NInput
            v-model:value="modalForm.secret"
            type="password"
            show-password-on="click"
            :placeholder="$t('exchange.webhooks.placeholder_secret')"
          />
          <template #feedback>
            <span v-if="modalAction === 'edit'" style="color: #999; font-size: 12px">
              {{ $t('exchange.webhooks.secret_edit_hint') }}
            </span>
          </template>
        </NFormItem>
        <NFormItem :label="$t('exchange.webhooks.form_active')" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem :label="$t('exchange.webhooks.form_remark')" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable :placeholder="$t('exchange.webhooks.placeholder_remark')" />
        </NFormItem>
      </NForm>

      <template #tip>
        <NAlert type="info" :title="$t('exchange.webhooks.tip_title')" class="mt-16">
          <template #header>{{ $t('exchange.webhooks.tip_header') }}</template>
          <ul style="margin: 0; padding-left: 16px">
            <li>{{ $t('exchange.webhooks.tip_1') }}</li>
            <li>{{ $t('exchange.webhooks.tip_2') }}</li>
            <li>{{ $t('exchange.webhooks.tip_3') }}</li>
          </ul>
        </NAlert>
      </template>
    </CrudModal>
  </CommonPage>
</template>
