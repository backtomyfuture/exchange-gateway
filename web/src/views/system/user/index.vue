  <script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NForm,
  NFormItem,
  NImage,
  NInput,
  NSpace,
  NSwitch,
  NTag,
  NPopconfirm,
  NDropdown,
  NTooltip,
  NTreeSelect,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
// import { loginTypeMap, loginTypeOptions } from '@/constant/data'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useUserStore } from '@/store'

defineOptions({ name: 'UserManagement' })

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
  name: t('system.user.name'),
  initForm: {},
  doCreate: api.createUser,
  doUpdate: api.updateUser,
  doDelete: api.deleteUser,
  refresh: () => $table.value?.handleSearch(),
})

const roleOption = ref([])
const deptOptions = ref([])


onMounted(() => {
  $table.value?.handleSearch()
  api.getRoleList({ page: 1, page_size: 9999 }).then((res) => (roleOption.value = res.data))
  api.getDepts().then((res) => (deptOptions.value = res.data))

})

const columns = [
  {
    title: () => t('system.user.col_name'),
    key: 'username',
    width: 60,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.user.col_email'),
    key: 'email',
    width: 60,
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.user.col_dept'),
    key: 'dept',
    width: 80,
    align: 'center',
    render(row) {
      return h(NTag, { type: 'default', bordered: false, style: { margin: '2px 3px' } }, { default: () => row?.dept?.name || t('system.user.no_dept') })
    },
  },
  {
    title: () => t('system.user.col_role'),
    key: 'role',
    width: 60,
    align: 'center',
    render(row) {
      const roles = row.roles ?? []
      const group = []
      for (let i = 0; i < roles.length; i++)
        group.push(
          h(NTag, { type: 'info', style: { margin: '2px 3px' } }, { default: () => roles[i].name })
        )
      return h('span', group)
    },
  },

  {
    title: () => t('system.user.col_superuser'),
    key: 'is_superuser',
    align: 'center',
    width: 40,
    render(row) {
      return h(
        NTag,
        { type: 'info', style: { margin: '2px 3px' } },
        { default: () => (row.is_superuser ? t('system.user.yes') : t('system.user.no')) }
      )
    },
  },
  {
    title: () => t('system.user.col_last_login'),
    key: 'last_login',
    align: 'center',
    width: 80,
    ellipsis: { tooltip: true },
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'text', ghost: true },
        {
          default: () => (row.last_login !== null ? formatDate(row.last_login) : null),
          icon: renderIcon('mdi:update', { size: 16 }),
        }
      )
    },
  },
  {
    title: () => t('system.user.col_disabled'),
    key: 'is_active',
    width: 50,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_active,
        loading: !!row.publishing,
        checkedValue: false,
        uncheckedValue: true,
        onUpdateValue: () => handleUpdateDisable(row),
      })
    },
  },
  {
    title: () => t('system.user.col_actions'),
    key: 'actions',
    width: 200,
    align: 'center',
    fixed: 'right',
    render(row) {
      const userStore = useUserStore()
      if (!userStore.isSuperUser && row.is_superuser) {
        return h(NTag, { type: 'default', size: 'small' }, { default: () => t('system.user.no_permission') })
      }

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
                modalForm.value.role_ids = row.roles.map((e) => (e = e.id))
              },
            },
            {
              default: () => t('system.user.btn_edit'),
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/user/update']]
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            style: 'margin-right: 8px;',
            onClick: () => handleAction('delete', row)
          },
          {
            default: () => t('system.user.btn_delete'),
            icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
          }
        ),
        !row.is_superuser && h(
          NButton,
          {
            size: 'small',
            type: 'warning',
            style: 'margin-right: 8px;',
            onClick: () => handleAction('reset_password', row)
          },
          {
            default: () => t('system.user.btn_reset_password'),
            icon: renderIcon('material-symbols:lock-reset', { size: 16 }),
          }
        ),
      ]
    },
  },
]

// 修改用户禁用状态
async function handleUpdateDisable(row) {
  if (!row.id) return
  const userStore = useUserStore()
  if (userStore.userId === row.id) {
    $message.error(t('system.user.cannot_disable_self'))
    return
  }
  if (!userStore.isSuperUser && row.is_superuser) {
    $message.error(t('system.user.cannot_disable_super'))
    return
  }
  row.publishing = true
  row.is_active = row.is_active === false ? true : false
  row.publishing = false
  const role_ids = []
  row.roles.forEach((e) => {
    role_ids.push(e.id)
  })
  row.role_ids = role_ids

  try {
    await api.updateUser(row)
    $message?.success(row.is_active ? t('system.user.enabled_user') : t('system.user.disabled_user'))
    $table.value?.handleSearch()
  } catch (err) {
    row.is_active = row.is_active === false ? true : false
  } finally {
    row.publishing = false
  }
}

function handleAction(key, row) {
  if (key === 'reset_password') {
    window.$dialog.warning({
      title: t('system.user.confirm_title'),
      content: t('system.user.confirm_reset_password'),
      positiveText: t('system.user.btn_confirm'),
      negativeText: t('system.user.btn_cancel'),
      onPositiveClick: async () => {
        try {
          await api.resetPassword({ user_id: row.id });
          window.$message.success(t('system.user.reset_password_success'));
          await $table.value?.handleSearch();
        } catch (error) {
          window.$message.error(t('system.user.reset_password_fail') + ': ' + error.message);
        }
      }
    })
  } else if (key === 'delete') {
    window.$dialog.warning({
      title: t('system.user.confirm_title'),
      content: t('system.user.confirm_delete_user'),
      positiveText: t('system.user.btn_confirm'),
      negativeText: t('system.user.btn_cancel'),
      onPositiveClick: () => handleDelete({ user_id: row.id }, false)
    })
  }
}



const validateAddUser = {
  username: [
    {
      required: true,
      message: () => t('system.user.validate_name_required'),
      trigger: ['input', 'blur'],
    },
  ],
  email: [
    {
      required: true,
      message: () => t('system.user.validate_email_required'),
      trigger: ['input', 'change'],
    },
    {
      trigger: ['blur'],
      validator: (rule, value, callback) => {
        const re = /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/
        if (!re.test(modalForm.value.email)) {
          callback(t('system.user.validate_email_format'))
          return
        }
        callback()
      },
    },
  ],
  password: [
    {
      required: true,
      message: () => t('system.user.validate_password_required'),
      trigger: ['input', 'blur', 'change'],
    },
  ],
  confirmPassword: [
    {
      required: true,
      message: () => t('system.user.validate_confirm_password_required'),
      trigger: ['input'],
    },
    {
      trigger: ['blur'],
      validator: (rule, value, callback) => {
        if (value !== modalForm.value.password) {
          callback(t('system.user.validate_password_mismatch'))
          return
        }
        callback()
      },
    },
  ],
  roles: [
    {
      type: 'array',
      required: true,
      message: () => t('system.user.validate_role_required'),
      trigger: ['blur', 'change'],
    },
  ],
}
</script>

<template>
  <CommonPage show-footer :title="$t('system.user.title')">
    <template #action>
      <NButton v-permission="'post/api/v1/user/create'" type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('system.user.add') }}
      </NButton>
    </template>
    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getUserList"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('system.user.query_name')" :label-width="40">
          <NInput
            v-model:value="queryItems.username"
            clearable
            type="text"
            :placeholder="$t('system.user.placeholder_name')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.user.query_email')" :label-width="40">
          <NInput
            v-model:value="queryItems.email"
            clearable
            type="text"
            :placeholder="$t('system.user.placeholder_email')"
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
        :rules="validateAddUser"
      >
        <NFormItem :label="$t('system.user.form_username')" path="username">
          <NInput v-model:value="modalForm.username" clearable :placeholder="$t('system.user.placeholder_form_name')" />
        </NFormItem>
        <NFormItem :label="$t('system.user.form_email')" path="email">
          <NInput v-model:value="modalForm.email" clearable :placeholder="$t('system.user.placeholder_form_email')" />
        </NFormItem>
        <NFormItem v-if="modalAction === 'add'" :label="$t('system.user.form_password')" path="password">
          <NInput
            v-model:value="modalForm.password"
            show-password-on="mousedown"
            type="password"
            clearable
            :placeholder="$t('system.user.placeholder_form_password')"
          />
        </NFormItem>
        <NFormItem v-if="modalAction === 'add'" :label="$t('system.user.form_confirm_password')" path="confirmPassword">
          <NInput
            v-model:value="modalForm.confirmPassword"
            show-password-on="mousedown"
            type="password"
            clearable
            :placeholder="$t('system.user.placeholder_form_confirm_password')"
          />
        </NFormItem>
        <NFormItem :label="$t('system.user.form_dept')" path="dept_id">
          <NTreeSelect
            v-model:value="modalForm.dept_id"
            :options="deptOptions"
            key-field="id"
            label-field="name"
            children-field="children"
            :placeholder="$t('system.user.placeholder_form_dept')"
            clearable
            default-expand-all
          />
        </NFormItem>
        <NFormItem :label="$t('system.user.form_role')" path="role_ids">
          <NCheckboxGroup v-model:value="modalForm.role_ids">
            <NSpace item-style="display: flex;">
              <NCheckbox
                v-for="item in roleOption"
                :key="item.id"
                :value="item.id"
                :label="item.name"
              />
            </NSpace>
          </NCheckboxGroup>
        </NFormItem>
        <NFormItem v-if="useUserStore().isSuperUser" :label="$t('system.user.form_superuser')" path="is_superuser">
          <NSwitch
            v-model:value="modalForm.is_superuser"
            size="small"
            :checked-value="true"
            :unchecked-value="false"
          ></NSwitch>
        </NFormItem>
        <NFormItem :label="$t('system.user.form_disabled')" path="is_active">
          <NSwitch
            v-model:value="modalForm.is_active"
            :checked-value="false"
            :unchecked-value="true"
            :default-value="true"
          />
        </NFormItem>

      </NForm>
    </CrudModal>
  </CommonPage>
  <!-- 业务页面 -->
</template>
