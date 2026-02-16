<script setup>
import { h, onMounted, ref } from 'vue'
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
    // 更新时不传 secret（如果为空）
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
  { label: '新邮件 (NewMailEvent)', value: 'NewMailEvent' },
  { label: '邮件创建 (CreatedEvent)', value: 'CreatedEvent' },
  { label: '邮件修改 (ModifiedEvent)', value: 'ModifiedEvent' },
  { label: '邮件删除 (DeletedEvent)', value: 'DeletedEvent' },
  { label: '邮件移动 (MovedEvent)', value: 'MovedEvent' },
  { label: '邮件复制 (CopiedEvent)', value: 'CopiedEvent' },
  { label: '忙闲状态变更 (FreeBusyChangedEvent)', value: 'FreeBusyChangedEvent' },
]

const columns = [
  {
    title: 'ID',
    key: 'id',
    width: 70,
    align: 'center',
  },
  {
    title: '回调地址',
    key: 'url',
    width: 250,
    ellipsis: { tooltip: true },
  },
  {
    title: '关联账户',
    key: 'account_id',
    width: 120,
    render(row) {
      const acc = accountOptions.value.find(a => a.value === row.account_id)
      return acc ? acc.label : `ID: ${row.account_id}`
    },
  },
  {
    title: '订阅事件',
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
    title: '状态',
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'default' },
        { default: () => (row.is_active ? '启用' : '禁用') }
      )
    },
  },
  {
    title: '备注',
    key: 'remark',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: '操作',
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
              default: () => '测试',
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
              default: () => '编辑',
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
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 14 }),
                  }
                ),
              default: () => '确定删除该Webhook订阅吗？',
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
      $message.success('测试请求已发送')
    } else {
      $message.error(res.msg || '测试失败')
    }
  } catch (err) {
    $message.error('测试失败: ' + err.message)
  }
}

// 删除
async function handleDelete(row) {
  try {
    const res = await api.deleteWebhook(row.id)
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

const validateForm = {
  account_id: [{ required: true, message: '请选择关联账户', trigger: 'change', type: 'number' }],
  url: [{ required: true, message: '请输入回调地址', trigger: 'input' }],
  events: [{ type: 'array', required: true, message: '请至少选择一个事件', trigger: 'change' }],
  secret: [
    { required: true, message: '请输入签名密钥', trigger: 'input' },
    { min: 8, message: '密钥至少8个字符', trigger: 'input' },
  ],
}
</script>

<template>
  <CommonPage show-footer title="Webhook订阅管理">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />创建Webhook
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
        <NFormItem label="关联账户" path="account_id">
          <NSelect
            v-model:value="modalForm.account_id"
            :options="accountOptions"
            placeholder="选择关联的邮箱账户"
            clearable
          />
        </NFormItem>
        <NFormItem label="回调地址" path="url">
          <NInput
            v-model:value="modalForm.url"
            placeholder="https://your-server.com/webhook"
            clearable
          />
        </NFormItem>
        <NFormItem label="订阅事件" path="events">
          <NSelect
            v-model:value="modalForm.events"
            multiple
            :options="eventOptions"
            placeholder="选择要订阅的事件"
          />
        </NFormItem>
        <NFormItem label="签名密钥" path="secret">
          <NInput
            v-model:value="modalForm.secret"
            type="password"
            show-password-on="click"
            placeholder="用于验签的密钥（至少8位）"
          />
          <template #feedback>
            <span v-if="modalAction === 'edit'" style="color: #999; font-size: 12px">
              留空则保持原密钥不变
            </span>
          </template>
        </NFormItem>
        <NFormItem label="启用状态" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem label="备注" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable placeholder="可选" />
        </NFormItem>
      </NForm>

      <template #tip>
        <NAlert type="info" title="Webhook 说明" class="mt-16">
          <template #header>回调地址要求</template>
          <ul style="margin: 0; padding-left: 16px">
            <li>回调地址必须是公网可访问的 HTTPS 地址</li>
            <li>不支持本地地址（localhost、127.0.0.1）</li>
            <li>私网地址根据配置可能受限</li>
          </ul>
        </NAlert>
      </template>
    </CrudModal>
  </CommonPage>
</template>
