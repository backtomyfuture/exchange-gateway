<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NSpace,
  NSwitch,
  NTag,
  NPopconfirm,
  NIcon,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: 'AccountManagement' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalTitle,
  modalAction,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: t('exchange.accounts.name'),
  initForm: { is_active: true },
  doCreate: api.createExchangeAccount,
  doUpdate: api.updateExchangeAccount,
  doDelete: api.deleteExchangeAccount,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

// 测试连接
const testLoading = ref({})
async function handleTest(row) {
  testLoading.value[row.id] = true
  try {
    const res = await api.testExchangeAccount({ account_id: row.id })
    if (res.code === 200) {
      $message.success(res.msg || t('exchange.accounts.test_success'))
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || t('exchange.accounts.test_fail'))
    }
  } catch (err) {
    $message.error(t('exchange.accounts.test_error') + ': ' + err.message)
  } finally {
    testLoading.value[row.id] = false
  }
}

const columns = [
  {
    title: 'ID',
    key: 'id',
    width: 60,
    align: 'center',
  },
  {
    title: () => t('exchange.accounts.col_email'),
    key: 'email',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.accounts.col_username'),
    key: 'username',
    width: 120,
    align: 'center',
  },
  {
    title: () => t('exchange.accounts.col_display_name'),
    key: 'display_name',
    width: 120,
    align: 'center',
  },
  {
    title: () => t('exchange.accounts.col_status'),
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'error' },
        { default: () => (row.is_active ? t('exchange.accounts.status_active') : t('exchange.accounts.status_inactive')) }
      )
    },
  },
  {
    title: () => t('exchange.accounts.col_verified'),
    key: 'is_verified',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_verified ? 'success' : 'warning' },
        { default: () => (row.is_verified ? t('exchange.accounts.verified') : t('exchange.accounts.unverified')) }
      )
    },
  },
  {
    title: () => t('exchange.accounts.col_last_verified'),
    key: 'last_verified_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.last_verified_at ? formatDate(row.last_verified_at) : '-'
    },
  },
  {
    title: () => t('exchange.accounts.col_created_at'),
    key: 'created_at',
    width: 160,
    align: 'center',
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: () => t('exchange.accounts.col_actions'),
    key: 'actions',
    width: 240,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        h(
          NButton,
          {
            size: 'small',
            type: 'info',
            style: 'margin-right: 8px;',
            loading: testLoading.value[row.id],
            onClick: () => handleTest(row),
          },
          {
            default: () => t('exchange.accounts.btn_test'),
            icon: renderIcon('mdi:connection', { size: 16 }),
          }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            style: 'margin-right: 8px;',
            onClick: () => handleEdit(row),
          },
          {
            default: () => t('exchange.accounts.btn_edit'),
            icon: renderIcon('material-symbols:edit', { size: 16 }),
          }
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ account_id: row.id }, false),
          },
          {
            trigger: () =>
              h(
                NButton,
                { size: 'small', type: 'error' },
                {
                  default: () => t('exchange.accounts.btn_delete'),
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => h('div', {}, t('exchange.accounts.confirm_delete')),
          }
        ),
      ]
    },
  },
]

const validateForm = {
  email: [
    { required: true, message: () => t('exchange.accounts.validate_email_required'), trigger: ['input', 'blur'] },
    { type: 'email', message: () => t('exchange.accounts.validate_email_format'), trigger: ['blur'] },
  ],
  username: [
    { required: true, message: () => t('exchange.accounts.validate_username_required'), trigger: ['input', 'blur'] },
  ],
  password: [
    { required: true, message: () => t('exchange.accounts.validate_password_required'), trigger: ['input', 'blur'] },
  ],
}
</script>

<template>
  <CommonPage show-footer :title="$t('exchange.accounts.title')">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('exchange.accounts.add') }}
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getExchangeAccounts"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('exchange.accounts.query_email')" :label-width="40">
          <NInput
            v-model:value="queryItems.email"
            clearable
            type="text"
            :placeholder="$t('exchange.accounts.placeholder_email')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 新增/编辑 弹窗 -->
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
        :rules="modalAction === 'add' ? validateForm : {}"
      >
        <NFormItem :label="$t('exchange.accounts.form_email')" path="email">
          <NInput
            v-model:value="modalForm.email"
            clearable
            :placeholder="$t('exchange.accounts.placeholder_form_email')"
            :disabled="modalAction === 'edit'"
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_username')" path="username">
          <NInput
            v-model:value="modalForm.username"
            clearable
            :placeholder="$t('exchange.accounts.placeholder_form_username')"
            :disabled="modalAction === 'edit'"
          />
        </NFormItem>
        <NFormItem :label="modalAction === 'add' ? $t('exchange.accounts.form_password') : $t('exchange.accounts.form_new_password')" path="password">
          <NInput
            v-model:value="modalForm.password"
            type="password"
            show-password-on="mousedown"
            clearable
            :placeholder="modalAction === 'add' ? $t('exchange.accounts.placeholder_form_password') : $t('exchange.accounts.placeholder_form_password_edit')"
          />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_display_name')" path="display_name">
          <NInput v-model:value="modalForm.display_name" clearable :placeholder="$t('exchange.accounts.placeholder_form_display_name')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_server')" path="server">
          <NInput v-model:value="modalForm.server" clearable :placeholder="$t('exchange.accounts.placeholder_form_server')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_domain')" path="domain">
          <NInput v-model:value="modalForm.domain" clearable :placeholder="$t('exchange.accounts.placeholder_form_domain')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_active')" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem :label="$t('exchange.accounts.form_remark')" path="remark">
          <NInput
            v-model:value="modalForm.remark"
            type="textarea"
            clearable
            :placeholder="$t('exchange.accounts.placeholder_form_remark')"
          />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
