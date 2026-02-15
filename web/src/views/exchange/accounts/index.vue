<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
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

defineOptions({ name: '邮箱账户管理' })

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
  name: '邮箱账户',
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
      $message.success(res.msg || '连接测试成功')
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || '连接测试失败')
    }
  } catch (err) {
    $message.error('测试失败: ' + err.message)
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
    title: '邮箱地址',
    key: 'email',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '用户名',
    key: 'username',
    width: 120,
    align: 'center',
  },
  {
    title: '显示名称',
    key: 'display_name',
    width: 120,
    align: 'center',
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
    title: '验证状态',
    key: 'is_verified',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_verified ? 'success' : 'warning' },
        { default: () => (row.is_verified ? '已验证' : '未验证') }
      )
    },
  },
  {
    title: '最后验证时间',
    key: 'last_verified_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.last_verified_at ? formatDate(row.last_verified_at) : '-'
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
            default: () => '测试连接',
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
            default: () => '编辑',
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
                  default: () => '删除',
                  icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                }
              ),
            default: () => h('div', {}, '确定删除该邮箱账户吗?'),
          }
        ),
      ]
    },
  },
]

const validateForm = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: ['input', 'blur'] },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur'] },
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: ['input', 'blur'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
  ],
}
</script>

<template>
  <CommonPage show-footer title="邮箱账户管理">
    <template #action>
      <NButton type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建账户
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
        <QueryBarItem label="邮箱" :label-width="40">
          <NInput
            v-model:value="queryItems.email"
            clearable
            type="text"
            placeholder="请输入邮箱"
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
        <NFormItem label="邮箱地址" path="email">
          <NInput
            v-model:value="modalForm.email"
            clearable
            placeholder="请输入邮箱地址"
            :disabled="modalAction === 'edit'"
          />
        </NFormItem>
        <NFormItem label="用户名" path="username">
          <NInput
            v-model:value="modalForm.username"
            clearable
            placeholder="登录用户名（不含域名）"
            :disabled="modalAction === 'edit'"
          />
        </NFormItem>
        <NFormItem :label="modalAction === 'add' ? '密码' : '新密码'" path="password">
          <NInput
            v-model:value="modalForm.password"
            type="password"
            show-password-on="mousedown"
            clearable
            :placeholder="modalAction === 'add' ? '请输入密码' : '留空则不修改'"
          />
        </NFormItem>
        <NFormItem label="显示名称" path="display_name">
          <NInput v-model:value="modalForm.display_name" clearable placeholder="可选" />
        </NFormItem>
        <NFormItem label="服务器" path="server">
          <NInput v-model:value="modalForm.server" clearable placeholder="可选，使用默认配置" />
        </NFormItem>
        <NFormItem label="域名" path="domain">
          <NInput v-model:value="modalForm.domain" clearable placeholder="可选，使用默认配置" />
        </NFormItem>
        <NFormItem label="启用" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
        <NFormItem label="备注" path="remark">
          <NInput
            v-model:value="modalForm.remark"
            type="textarea"
            clearable
            placeholder="可选"
          />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
