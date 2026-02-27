<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NPopconfirm,
  NSwitch,
  NTreeSelect,
  NRadio,
  NRadioGroup,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import IconPicker from '@/components/icon/IconPicker.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '菜单管理' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 表单初始化内容
const initForm = {
  order: 1,
  keepalive: true,
}

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleAdd,
  handleDelete,
  handleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '菜单',
  initForm,
  doCreate: api.createMenu,
  doDelete: api.deleteMenu,
  doUpdate: api.updateMenu,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
  getTreeSelect()
})

const showMenuType = ref(false)
const menuOptions = ref([])

const columns = [
  { title: () => t('system.menu.col_id'), key: 'id', width: 50, ellipsis: { tooltip: true }, align: 'center' },
  { title: () => t('system.menu.col_name'), key: 'name', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  {
    title: () => t('system.menu.col_type'),
    key: 'menu_type',
    width: 80,
    align: 'center',
    ellipsis: { tooltip: true },
    render(row) {
      let round = false
      let bordered = false
      if (row.menu_type === 'catalog') {
        bordered = true
        round = false
      } else if (row.menu_type === 'menu') {
        bordered = false
        round = true
      }
      return h(
        NTag,
        { type: 'primary', round: round, bordered: bordered },
        { default: () => (row.menu_type === 'catalog' ? t('system.menu.type_catalog') : t('system.menu.type_menu')) }
      )
    },
  },
  {
    title: () => t('system.menu.col_icon'),
    key: 'icon',
    width: 40,
    align: 'center',
    render(row) {
      return h(TheIcon, { icon: row.icon, size: 20 })
    },
  },
  { title: () => t('system.menu.col_order'), key: 'order', width: 40, ellipsis: { tooltip: true }, align: 'center' },
  { title: () => t('system.menu.col_path'), key: 'path', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  { title: () => t('system.menu.col_redirect'), key: 'redirect', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  { title: () => t('system.menu.col_component'), key: 'component', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  {
    title: () => t('system.menu.col_keepalive'),
    key: 'keepalive',
    width: 40,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.keepalive,
        onUpdateValue: () => handleUpdateKeepalive(row),
      })
    },
  },
  {
    title: () => t('system.menu.col_hidden'),
    key: 'is_hidden',
    width: 40,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_hidden,
        onUpdateValue: () => handleUpdateHidden(row),
      })
    },
  },
  {
    title: () => t('system.menu.col_created_at'),
    key: 'created_at',
    width: 80,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.created_at))
    },
  },
  {
    title: () => t('system.menu.col_actions'),
    key: 'actions',
    width: 120,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'primary',
              style: `display: ${row.children && row.menu_type !== 'menu' ? '' : 'none'};`,
              onClick: () => {
                initForm.parent_id = row.id
                initForm.menu_type = 'menu'
                showMenuType.value = false
                handleAdd()
              },
            },
            { default: () => t('system.menu.btn_add_child'), icon: renderIcon('material-symbols:add', { size: 16 }) }
          ),
          [[vPermission, 'post/api/v1/menu/create']]
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'info',
              onClick: () => {
                showMenuType.value = false
                handleEdit(row)
              },
            },
            {
              default: () => t('system.menu.btn_edit'),
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/menu/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ id: row.id }, false),
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'tiny',
                    quaternary: true,
                    type: 'error',
                    style: `display: ${row.children && row.children.length > 0 ? 'none' : ''};`,
                  },
                  {
                    default: () => t('system.menu.btn_delete'),
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/menu/delete']]
              ),
            default: () => h('div', {}, t('system.menu.confirm_delete')),
          }
        ),
      ]
    },
  },
]
// 修改是否keepalive
async function handleUpdateKeepalive(row) {
  if (!row.id) return
  row.publishing = true
  row.keepalive = row.keepalive === false ? true : false
  await api.updateMenu(row)
  row.publishing = false
  $message?.success(row.keepalive ? t('system.menu.keepalive_on') : t('system.menu.keepalive_off'))
}

// 修改是否隐藏
async function handleUpdateHidden(row) {
  if (!row.id) return
  row.publishing = true
  row.is_hidden = row.is_hidden === false ? true : false
  await api.updateMenu(row)
  row.publishing = false
  $message?.success(row.is_hidden ? t('system.menu.hidden_on') : t('system.menu.hidden_off'))
}

// 新增菜单(可选目录)
function handleClickAdd() {
  initForm.parent_id = 0
  initForm.menu_type = 'catalog'
  initForm.is_hidden = false
  initForm.order = 1
  initForm.keepalive = true
  showMenuType.value = true
  handleAdd()
}

async function getTreeSelect() {
  const { data } = await api.getMenus()
  const menu = { id: 0, name: t('system.menu.root_menu'), children: [] }
  menu.children = data
  menuOptions.value = [menu]
}
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer :title="$t('system.menu.title')">
    <template #action>
      <NButton v-permission="'post/api/v1/menu/create'" type="primary" @click="handleClickAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />{{ $t('system.menu.add') }}
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :is-pagination="false"
      :columns="columns"
      :get-data="api.getMenus"
      :single-line="true"
    >
    </CrudTable>

    <!-- 新增/编辑/查看 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave(getTreeSelect)"
    >
      <!-- 表单 -->
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
      >
        <NFormItem :label="$t('system.menu.form_type')" path="menu_type">
          <NRadioGroup v-model:value="modalForm.menu_type">
            <NRadio :label="$t('system.menu.radio_catalog')" value="catalog" />
            <NRadio :label="$t('system.menu.radio_menu')" value="menu" />
          </NRadioGroup>
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_parent')" path="parent_id">
          <NTreeSelect
            v-model:value="modalForm.parent_id"
            key-field="id"
            label-field="name"
            :options="menuOptions"
            default-expand-all="true"
          />
        </NFormItem>
        <NFormItem
          :label="$t('system.menu.form_name')"
          path="name"
          :rule="{
            required: true,
            message: $t('system.menu.validate_name_required'),
            trigger: ['input', 'blur'],
          }"
        >
          <NInput v-model:value="modalForm.name" :placeholder="$t('system.menu.placeholder_name')" />
        </NFormItem>
        <NFormItem
          :label="$t('system.menu.form_path')"
          path="path"
          :rule="{
            required: true,
            message: $t('system.menu.validate_path_required'),
            trigger: ['blur'],
          }"
        >
          <NInput v-model:value="modalForm.path" :placeholder="$t('system.menu.placeholder_path')" />
        </NFormItem>
        <NFormItem v-if="modalForm.menu_type === 'menu'" :label="$t('system.menu.form_component')" path="component">
          <NInput
            v-model:value="modalForm.component"
            :placeholder="$t('system.menu.placeholder_component')"
          />
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_redirect')" path="redirect">
          <NInput
            v-model:value="modalForm.redirect"
            :disabled="modalForm.parent_id !== 0"
            :placeholder="
              modalForm.parent_id !== 0 ? $t('system.menu.placeholder_redirect_disabled') : $t('system.menu.placeholder_redirect')
            "
          />
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_icon')" path="icon">
          <IconPicker v-model:value="modalForm.icon" />
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_order')" path="order">
          <NInputNumber v-model:value="modalForm.order" :min="1" />
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_hidden')" path="is_hidden">
          <NSwitch v-model:value="modalForm.is_hidden" />
        </NFormItem>
        <NFormItem :label="$t('system.menu.form_keepalive')" path="keepalive">
          <NSwitch v-model:value="modalForm.keepalive" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
