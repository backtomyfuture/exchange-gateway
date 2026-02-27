<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton, NForm, NFormItem, NInput, NPopconfirm } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'

defineOptions({ name: 'API管理' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: 'API',
  initForm: {},
  doCreate: api.createApi,
  doUpdate: api.updateApi,
  doDelete: api.deleteApi,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

async function handleRefreshApi() {
  await $dialog.confirm({
    title: t('system.api.refresh_confirm_title'),
    type: 'warning',
    content: t('system.api.refresh_confirm_content'),
    async confirm() {
      await api.refreshApi()
      $message.success(t('system.api.refresh_success'))
      $table.value?.handleSearch()
    },
  })
}

const addAPIRules = {
  path: [
    {
      required: true,
      message: () => t('system.api.validate_path_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
  method: [
    {
      required: true,
      message: () => t('system.api.validate_method_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
  summary: [
    {
      required: true,
      message: () => t('system.api.validate_summary_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
  tags: [
    {
      required: true,
      message: () => t('system.api.validate_tags_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

const columns = [
  {
    title: () => t('system.api.col_path'),
    key: 'path',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.api.col_method'),
    key: 'method',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.api.col_summary'),
    key: 'summary',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.api.col_tags'),
    key: 'tags',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.api.col_actions'),
    key: 'actions',
    width: 'auto',
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              style: 'margin-right: 8px;',
              onClick: () => {
                handleEdit(row)
                modalForm.value.roles = row.roles.map((e) => (e = e.id))
              },
            },
            {
              default: () => t('system.api.btn_edit'),
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/api/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ api_id: row.id }, false),
            onNegativeClick: () => {},
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    style: 'margin-right: 8px;',
                  },
                  {
                    default: () => t('system.api.btn_delete'),
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/api/delete']]
              ),
            default: () => h('div', {}, t('system.api.confirm_delete')),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer :title="$t('system.api.title')">
    <template #action>
      <div>
        <NButton
          v-permission="'post/api/v1/api/create'"
          class="float-right mr-15"
          type="primary"
          @click="handleAdd"
        >
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('system.api.add') }}
        </NButton>
        <NButton
          v-permission="'post/api/v1/api/refresh'"
          class="float-right mr-15"
          type="warning"
          @click="handleRefreshApi"
        >
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />{{ $t('system.api.btn_refresh') }}
        </NButton>
      </div>
    </template>
    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getApis"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('system.api.query_path')" :label-width="40">
          <NInput
            v-model:value="queryItems.path"
            clearable
            type="text"
            :placeholder="$t('system.api.placeholder_path')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.api.query_summary')" :label-width="70">
          <NInput
            v-model:value="queryItems.summary"
            clearable
            type="text"
            :placeholder="$t('system.api.placeholder_summary')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.api.query_tags')" :label-width="40">
          <NInput
            v-model:value="queryItems.tags"
            clearable
            type="text"
            :placeholder="$t('system.api.placeholder_tags')"
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
        :label-width="80"
        :model="modalForm"
        :rules="addAPIRules"
      >
        <NFormItem :label="$t('system.api.form_path')" path="path">
          <NInput v-model:value="modalForm.path" clearable :placeholder="$t('system.api.placeholder_form_path')" />
        </NFormItem>
        <NFormItem :label="$t('system.api.form_method')" path="method">
          <NInput v-model:value="modalForm.method" clearable :placeholder="$t('system.api.placeholder_form_method')" />
        </NFormItem>
        <NFormItem :label="$t('system.api.form_summary')" path="summary">
          <NInput v-model:value="modalForm.summary" clearable :placeholder="$t('system.api.placeholder_form_summary')" />
        </NFormItem>
        <NFormItem :label="$t('system.api.form_tags')" path="tags">
          <NInput v-model:value="modalForm.tags" clearable :placeholder="$t('system.api.placeholder_form_tags')" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
