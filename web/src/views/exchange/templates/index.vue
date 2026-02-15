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
  { label: '纯文本', value: 'text' },
]

const columns = [
  {
    title: '模板名称',
    key: 'name',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: '主题',
    key: 'subject',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '分类',
    key: 'category',
    width: 100,
    align: 'center',
    render(row) {
      return row.category ? h(NTag, { size: 'small' }, { default: () => row.category }) : '-'
    },
  },
  {
    title: '变量',
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
    title: '类型',
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
    title: '状态',
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'error' },
        { default: () => (row.is_active ? '启用' : '禁用') }
      )
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    align: 'center',
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: '操作',
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
            default: () => '预览',
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
            default: () => '编辑',
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
                  default: () => '删除',
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => h('div', {}, '确定删除该模板吗?'),
          }
        ),
      ]
    },
  },
]

const validateForm = {
  name: [
    { required: true, message: '请输入模板名称', trigger: ['input', 'blur'] },
  ],
  subject: [
    { required: true, message: '请输入邮件主题', trigger: ['input', 'blur'] },
  ],
  body: [
    { required: true, message: '请输入邮件正文', trigger: ['input', 'blur'] },
  ],
}
</script>

<template>
  <CommonPage show-footer title="邮件模板管理">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建模板
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
        <QueryBarItem label="名称" :label-width="40">
          <NInput
            v-model:value="queryItems.name"
            clearable
            type="text"
            placeholder="搜索模板名称"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="分类" :label-width="40">
          <NInput
            v-model:value="queryItems.category"
            clearable
            placeholder="分类标签"
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
        <NFormItem label="模板名称" path="name">
          <NInput v-model:value="modalForm.name" clearable placeholder="如：订单通知" />
        </NFormItem>
        <NFormItem label="分类标签" path="category">
          <NInput v-model:value="modalForm.category" clearable placeholder="可选，如：通知、营销" />
        </NFormItem>
        <NFormItem label="邮件主题" path="subject">
          <NInput v-model:value="modalForm.subject" clearable placeholder="支持变量 {{name}}" />
        </NFormItem>
        <NFormItem label="正文类型" path="body_type">
          <NSelect v-model:value="modalForm.body_type" :options="bodyTypeOptions" />
        </NFormItem>
        <NFormItem label="邮件正文" path="body">
          <!-- HTML 模式：富文本编辑器 -->
          <RichTextEditor
            v-if="modalForm.body_type === 'html'"
            v-model="modalForm.body"
            placeholder="支持粘贴图片，支持变量 {{variable}}"
            height="400px"
          />
          <!-- 纯文本模式：普通文本框 -->
          <NInput
            v-else
            v-model:value="modalForm.body"
            type="textarea"
            placeholder="支持变量 {{variable}}"
            :autosize="{ minRows: 8, maxRows: 15 }"
          />
        </NFormItem>
        <NAlert type="info" title="变量说明" style="margin-bottom: 16px">
          使用 <code>{{变量名}}</code> 语法定义变量，发送时传入对应的值进行替换。
          <br />例如：<code>尊敬的 {{customer_name}}，您的订单 {{order_id}} 已发货。</code>
        </NAlert>
        <NFormItem label="启用" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem label="备注" path="remark">
          <NInput v-model:value="modalForm.remark" type="textarea" clearable placeholder="可选" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 预览弹窗 -->
    <CrudModal
      v-model:visible="previewVisible"
      title="模板预览"
      :show-footer="false"
      style="width: 700px; max-width: 90vw"
    >
      <div class="preview-subject">
        <strong>主题：</strong>{{ previewData.subject }}
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
