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
  NSwitch,
  NAlert,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'
import RichTextEditor from '@/components/editor/RichTextEditor.vue'

defineOptions({ name: '邮件模板管理' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})

// 预览弹窗
const previewVisible = ref(false)
const previewData = ref({ subject: '', body: '' })

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
  name: '邮件模板',
  initForm: { 
    body_type: 'html', 
    is_active: true,
    variables: [],
  },
  doCreate: api.createEmailTemplate,
  doUpdate: api.updateEmailTemplate,
  doDelete: api.deleteEmailTemplate,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

// 预览模板
async function handlePreview(row) {
  previewData.value = {
    subject: row.subject,
    body: row.body,
  }
  previewVisible.value = true
}

const bodyTypeOptions = [
  { label: 'HTML', value: 'html' },
  { label: () => t('exchange.templates.type_plain_text'), value: 'text' },
]

const columns = [
  {
    title: () => t('exchange.templates.col_name'),
    key: 'name',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.templates.col_subject'),
    key: 'subject',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.templates.col_category'),
    key: 'category',
    width: 100,
    align: 'center',
    render(row) {
      return row.category ? h(NTag, { size: 'small' }, { default: () => row.category }) : '-'
    },
  },
  {
    title: () => t('exchange.templates.col_variables'),
    key: 'variables',
    width: 150,
    render(row) {
      const vars = row.variables || []
      if (vars.length === 0) return '-'
      return h(
        NSpace,
        { size: 'small' },
        { default: () => vars.slice(0, 3).map(v => 
          h(NTag, { size: 'small', type: 'info' }, { default: () => `{{${v}}}` })
        )}
      )
    },
  },
  {
    title: () => t('exchange.templates.col_type'),
    key: 'body_type',
    width: 80,
    align: 'center',
    render(row) {
      return h(NTag, { 
        size: 'small', 
        type: row.body_type === 'html' ? 'success' : 'default' 
      }, { default: () => row.body_type.toUpperCase() })
    },
  },
  {
    title: () => t('exchange.templates.col_status'),
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'error' },
        { default: () => (row.is_active ? t('exchange.templates.status_active') : t('exchange.templates.status_inactive')) }
      )
    },
  },
  {
    title: () => t('exchange.templates.col_created_at'),
    key: 'created_at',
    width: 160,
    align: 'center',
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: () => t('exchange.templates.col_actions'),
    key: 'actions',
    width: 200,
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
            onClick: () => handlePreview(row),
          },
          {
            default: () => t('exchange.templates.btn_preview'),
            icon: renderIcon('mdi:eye', { size: 16 }),
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
            default: () => t('exchange.templates.btn_edit'),
            icon: renderIcon('material-symbols:edit', { size: 16 }),
          }
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ template_id: row.id }, false),
          },
          {
            trigger: () =>
              h(
                NButton,
                { size: 'small', type: 'error' },
                {
                  default: () => t('exchange.templates.btn_delete'),
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => h('div', {}, t('exchange.templates.confirm_delete')),
          }
        ),
      ]
    },
  },
]

const validateForm = {
  name: [
    { required: true, message: () => t('exchange.templates.validate_name_required'), trigger: ['input', 'blur'] },
  ],
  subject: [
    { required: true, message: () => t('exchange.templates.validate_subject_required'), trigger: ['input', 'blur'] },
  ],
  body: [
    { required: true, message: () => t('exchange.templates.validate_body_required'), trigger: ['input', 'blur'] },
  ],
}
</script>

<template>
  <CommonPage show-footer :title="$t('exchange.templates.title')">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('exchange.templates.add') }}
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getEmailTemplates"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('exchange.templates.query_name')" :label-width="40">
          <NInput
            v-model:value="queryItems.name"
            clearable
            type="text"
            :placeholder="$t('exchange.templates.placeholder_search_name')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('exchange.templates.query_category')" :label-width="40">
          <NInput
            v-model:value="queryItems.category"
            clearable
            :placeholder="$t('exchange.templates.placeholder_search_category')"
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
      style="width: 700px; max-width: 90vw"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="validateForm"
      >
        <NFormItem :label="$t('exchange.templates.form_name')" path="name">
          <NInput v-model:value="modalForm.name" clearable :placeholder="$t('exchange.templates.placeholder_name')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.templates.form_category')" path="category">
          <NInput v-model:value="modalForm.category" clearable :placeholder="$t('exchange.templates.placeholder_category')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.templates.form_subject')" path="subject">
          <NInput v-model:value="modalForm.subject" clearable :placeholder="$t('exchange.templates.placeholder_subject')" />
        </NFormItem>
        <NFormItem :label="$t('exchange.templates.form_body_type')" path="body_type">
          <NSelect v-model:value="modalForm.body_type" :options="bodyTypeOptions" />
        </NFormItem>
        <NFormItem :label="$t('exchange.templates.form_body')" path="body">
          <!-- HTML 模式：富文本编辑器 -->
          <RichTextEditor
            v-if="modalForm.body_type === 'html'"
            v-model="modalForm.body"
            :placeholder="$t('exchange.templates.placeholder_body_html')"
            height="400px"
          />
          <!-- 纯文本模式：普通文本框 -->
          <NInput
            v-else
            v-model:value="modalForm.body"
            type="textarea"
            :placeholder="$t('exchange.templates.placeholder_body_text')"
            :autosize="{ minRows: 8, maxRows: 15 }"
          />
        </NFormItem>
        <NAlert type="info" :title="$t('exchange.templates.variable_tip_title')" style="margin-bottom: 16px">
          {{ $t('exchange.templates.variable_tip_content') }}
          <br />{{ $t('exchange.templates.variable_tip_example') }}
        </NAlert>
        <NFormItem :label="$t('exchange.templates.form_active')" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem :label="$t('exchange.templates.form_remark')" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable :placeholder="$t('exchange.templates.placeholder_remark')" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 预览弹窗 -->
    <CrudModal
      v-model:visible="previewVisible"
      :title="$t('exchange.templates.preview_title')"
      :show-footer="false"
      style="width: 700px; max-width: 90vw"
    >
      <div class="preview-subject">
        <strong>{{ $t('exchange.templates.preview_subject') }}</strong>{{ previewData.subject }}
      </div>
      <div class="preview-body" v-html="previewData.body"></div>
    </CrudModal>
  </CommonPage>
</template>

<style scoped>
.preview-subject {
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 16px;
}

.preview-body {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  min-height: 200px;
  background: white;
  overflow: auto;
}

/* 限制预览中的图片宽度 */
.preview-body :deep(img) {
  max-width: 100%;
  height: auto;
}
</style>
