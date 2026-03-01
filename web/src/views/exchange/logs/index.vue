<script setup>
import { h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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

defineOptions({ name: 'EmailLogs' })

const { t } = useI18n()

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
  { label: () => t('exchange.logs.action_all'), value: null },
  { label: () => t('exchange.logs.action_send'), value: 'send' },
  { label: () => t('exchange.logs.action_receive'), value: 'receive' },
  { label: () => t('exchange.logs.action_sync'), value: 'sync' },
  { label: () => t('exchange.logs.action_search'), value: 'search' },
  { label: () => t('exchange.logs.action_draft'), value: 'create_draft' },
  { label: () => t('exchange.logs.action_folders'), value: 'folders' },
  { label: () => t('exchange.logs.action_read'), value: 'mark_read' },
  { label: () => t('exchange.logs.action_unread'), value: 'mark_unread' },
  { label: () => t('exchange.logs.action_reply'), value: 'reply' },
  { label: () => t('exchange.logs.action_forward'), value: 'forward' },
  { label: () => t('exchange.logs.action_delete'), value: 'delete' },
]

const statusOptions = [
  { label: () => t('exchange.logs.status_all'), value: null },
  { label: () => t('exchange.logs.status_success'), value: 'success' },
  { label: () => t('exchange.logs.status_failed'), value: 'failed' },
  { label: () => t('exchange.logs.status_pending'), value: 'pending' },
]

const columns = [
  {
    title: () => t('exchange.logs.col_action'),
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
      const actionKeyMap = {
        send: 'exchange.logs.action_send',
        receive: 'exchange.logs.action_receive',
        sync: 'exchange.logs.action_sync',
        search: 'exchange.logs.action_search',
        create_draft: 'exchange.logs.action_draft',
        folders: 'exchange.logs.action_folders',
        mark_read: 'exchange.logs.action_read',
        mark_unread: 'exchange.logs.action_unread',
        reply: 'exchange.logs.action_reply',
        forward: 'exchange.logs.action_forward',
        delete: 'exchange.logs.action_delete',
        move: 'exchange.logs.action_move',
        list_folders: 'exchange.logs.action_folders',
      }
      return h(
        NTag,
        { type: colors[row.action] || 'default', size: 'small' },
        { default: () => actionKeyMap[row.action] ? t(actionKeyMap[row.action]) : row.action }
      )
    },
  },
  {
    title: () => t('exchange.logs.col_account_email'),
    key: 'account_email',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('exchange.logs.col_api_key'),
    key: 'api_key_name',
    width: 120,
    align: 'center',
    render(row) {
      return row.api_key_name || '-'
    },
  },
  {
    title: () => t('exchange.logs.col_subject'),
    key: 'subject',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      return row.subject || '-'
    },
  },
  {
    title: () => t('exchange.logs.col_recipients'),
    key: 'recipients',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      const recipients = row.recipients || []
      return recipients.length > 0 ? recipients.join(', ') : '-'
    },
  },
  {
    title: () => t('exchange.logs.col_status'),
    key: 'status',
    width: 80,
    align: 'center',
    render(row) {
      const colors = {
        success: 'success',
        failed: 'error',
        pending: 'warning',
      }
      const statusKeyMap = {
        success: 'exchange.logs.status_success',
        failed: 'exchange.logs.status_failed',
        pending: 'exchange.logs.status_pending',
      }
      return h(
        NTag,
        { type: colors[row.status] || 'default', size: 'small' },
        { default: () => statusKeyMap[row.status] ? t(statusKeyMap[row.status]) : row.status }
      )
    },
  },
  {
    title: () => t('exchange.logs.col_request_ip'),
    key: 'request_ip',
    width: 120,
    align: 'center',
    render(row) {
      return row.request_ip || '-'
    },
  },
  {
    title: () => t('exchange.logs.col_time'),
    key: 'created_at',
    width: 160,
    align: 'center',
    render(row) {
      return formatDate(row.created_at)
    },
  },
  {
    title: () => t('exchange.logs.col_error'),
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
  <CommonPage show-footer :title="$t('exchange.logs.title')">
    <!-- 统计卡片 -->
    <NGrid :cols="4" :x-gap="16" style="margin-bottom: 16px">
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.logs.stat_total')" :value="stats.total_count || 0" />
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.logs.stat_success')" :value="stats.success_count || 0">
            <template #suffix>
              <span style="color: #18a058">✓</span>
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.logs.stat_failed')" :value="stats.failed_count || 0">
            <template #suffix>
              <span style="color: #d03050">✗</span>
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.logs.stat_success_rate')" :value="stats.success_rate || 0">
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
        <QueryBarItem :label="$t('exchange.logs.query_action')" :label-width="60">
          <NSelect
            v-model:value="queryItems.action"
            :options="actionOptions"
            clearable
            style="width: 120px"
            @update:value="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('exchange.logs.query_status')" :label-width="40">
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
