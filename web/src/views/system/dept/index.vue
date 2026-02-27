<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NPopconfirm, NTreeSelect } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'

defineOptions({ name: '部门管理' })

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
  initForm: { order: 0 },
  doCreate: api.createDept,
  doUpdate: api.updateDept,
  doDelete: api.deleteDept,
  refresh: () => $table.value?.handleSearch(),
})

const deptOption = ref([])
const isDisabled = ref(false)

onMounted(() => {
  $table.value?.handleSearch()
  api.getDepts().then((res) => (deptOption.value = res.data))
})

const deptRules = {
  name: [
    {
      required: true,
      message: () => t('system.dept.validate_name_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

async function addDepts() {
  isDisabled.value = false
  handleAdd()
}

const columns = [
  {
    title: () => t('system.dept.col_name'),
    key: 'name',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.dept.col_desc'),
    key: 'desc',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.dept.col_actions'),
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
              style: 'margin-left: 8px;',
              onClick: () => {
                console.log('row', row.parent_id)
                if (row.parent_id === 0) {
                  isDisabled.value = true
                } else {
                  isDisabled.value = false
                }
                handleEdit(row)
              },
            },
            {
              default: () => t('system.dept.btn_edit'),
              icon: renderIcon('material-symbols:edit', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/dept/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ dept_id: row.id }, false),
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
                    style: 'margin-left: 8px;',
                  },
                  {
                    default: () => t('system.dept.btn_delete'),
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/dept/delete']]
              ),
            default: () => h('div', {}, t('system.dept.confirm_delete')),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer :title="$t('system.dept.title')">
    <template #action>
      <div>
        <NButton
          v-permission="'post/api/v1/dept/create'"
          class="float-right mr-15"
          type="primary"
          @click="addDepts"
        >
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('system.dept.add') }}
        </NButton>
      </div>
    </template>
    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getDepts"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('system.dept.query_name')" :label-width="80">
          <NInput
            v-model:value="queryItems.name"
            clearable
            type="text"
            :placeholder="$t('system.dept.placeholder_name')"
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
        :rules="deptRules"
      >
        <NFormItem :label="$t('system.dept.form_parent')" path="parent_id">
          <NTreeSelect
            v-model:value="modalForm.parent_id"
            :options="deptOption"
            key-field="id"
            label-field="name"
            :placeholder="$t('system.dept.placeholder_form_parent')"
            clearable
            default-expand-all
            :disabled="isDisabled"
          ></NTreeSelect>
        </NFormItem>
        <NFormItem :label="$t('system.dept.form_name')" path="name">
          <NInput v-model:value="modalForm.name" clearable :placeholder="$t('system.dept.placeholder_form_name')" />
        </NFormItem>
        <NFormItem :label="$t('system.dept.form_desc')" path="desc">
          <NInput v-model:value="modalForm.desc" type="textarea" clearable />
        </NFormItem>
        <NFormItem :label="$t('system.dept.form_order')" path="order">
          <NInputNumber v-model:value="modalForm.order" min="0"></NInputNumber>
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
