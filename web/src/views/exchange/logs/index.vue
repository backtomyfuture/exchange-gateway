<script setup>
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NTag,
  NSelect,
  NStatistic,
  NCard,
  NGrid,
  NGi,
  NProgress,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import api from '@/api'

defineOptions({ name: '邮件日志' })

const $table = ref(null)
const queryItems = ref({})
const stats = ref({})

onMounted(async () => {
  $table.value?.handleSearch()
  loadStats()
})

async function loadStats() {
  try {
    const res = await api.getExchangeStats()
    if (res.code === 200) {
      stats.value = res.data || {}
    }
  } catch (err) {
    console.error('加载统计失败', err)
  }
}

const actionOptions = [
  { label: '全部', value: null },
  { label: '发送', value: 'send' },
  { label: '接收', value: 'receive' },
  { label: '同步', value: 'sync' },
  { label: '搜索', value: 'search' },
  { label: '草稿', value: 'create_draft' },
  { label: '文件夹', value: 'folders' },
  { label: '已读', value: 'mark_read' },
  { label: '未读', value: 'mark_unread' },
  { label: '回复', value: 'reply' },
  { label: '转发', value: 'forward' },
  { label: '删除', value: 'delete' },
]

const statusOptions = [
  { label: '全部', value: null },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '进行中', value: 'pending' },
]

const actionMap = {
  send: '发送',
  receive: '接收',
  sync: '同步',
  search: '搜索',
  create_draft: '草稿',
  folders: '文件夹',
  mark_read: '已读',
  mark_unread: '未读',
  reply: '回复',
  forward: '转发',
  delete: '删除',
  move: '移动',
  list_folders: '文件夹', // Legacy?
}

const columns = [
  {
    title: '操作类型',
    key: 'action',
    width: 100,
    align: 'center',
    render(row) {
      const colors = {
        send: 'info',
        receive: 'success',
        reply: 'info',
        forward: 'info',
        search: 'warning',
        delete: 'error',
      }
      return h(
        NTag,
        { type: colors[row.action] || 'default', size: 'small' },
        { default: () => actionMap[row.action] || row.action }
      )
    },
  },
  {
    title: '邮箱账户',
    key: 'account_email',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: 'API密钥',
    key: 'api_key_name',
    width: 120,
    align: 'center',
    render(row) {
      return row.api_key_name || '-'
    },
  },
  {
    title: '主题',
    key: 'subject',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      return row.subject || '-'
    },
  },
  {
    title: '收件人',
    key: 'recipients',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      const recipients = row.recipients || []
      return recipients.length > 0 ? recipients.join(', ') : '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 80,
    align: 'center',
    render(row) {
      const colors = {
        success: 'success',
        failed: 'error',
        pending: 'warning',
      }
      const labels = {
        success: '成功',
        failed: '失败',
        pending: '进行中',
      }
      return h(
        NTag,
        { type: colors[row.status] || 'default', size: 'small' },
        { default: () => labels[row.status] || row.status }
      )
    },
  },
  {
    title: '请求IP',
    key: 'request_ip',
    width: 120,
    align: 'center',
    render(row) {
      return row.request_ip || '-'
    },
  },
  {
    title: '时间',
    key: 'created_at',
    width: 160,
    align: 'center',
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: '错误信息',
    key: 'error_message',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      if (row.error_message) {
        return h(NTag, { type: 'error', size: 'small' }, { default: () => row.error_message })
      }
      return '-'
    },
  },
]
</script>

<template>
  <CommonPage show-footer title="邮件日志">
    <!-- 统计卡片 -->
    <NGrid :cols="4" :x-gap="16" style="margin-bottom: 16px">
      <NGi>
        <NCard>
          <NStatistic label="总请求数" :value="stats.total_count || 0" />
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="成功数" :value="stats.success_count || 0">
            <template #suffix>
              <span style="color: #18a058">✓</span>
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="失败数" :value="stats.failed_count || 0">
            <template #suffix>
              <span style="color: #d03050">✗</span>
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="成功率" :value="stats.success_rate || 0">
            <template #prefix>
              <TheIcon icon="mdi:chart-arc" :size="24" style="color: #18a058" />
            </template>
            <template #suffix>
                <span class="text-20">%</span>
            </template>
          </NStatistic>
        </NCard>
      </NGi>
    </NGrid>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getExchangeLogs"
      :show-query-bar-actions="false"
    >
      <template #queryBar>
        <QueryBarItem label="操作类型" :label-width="60">
          <NSelect
            v-model:value="queryItems.action"
            :options="actionOptions"
            clearable
            style="width: 120px"
            @update:value="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="状态" :label-width="40">
          <NSelect
            v-model:value="queryItems.status"
            :options="statusOptions"
            clearable
            style="width: 100px"
            @update:value="$table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
