<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NInput, NSelect } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import api from '@/api'

defineOptions({ name: 'AuditLog' })

const { t } = useI18n()

const $table = ref(null)
const queryItems = ref({})

onMounted(() => {
  $table.value?.handleSearch()
})

function formatTimestamp(timestamp) {
  const date = new Date(timestamp)

  const pad = (num) => num.toString().padStart(2, '0')

  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())
  const seconds = pad(date.getSeconds())

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function getStartOfDayTimestamp() {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return now.getTime()
}

function getEndOfDayTimestamp() {
  const now = new Date()
  now.setHours(23, 59, 59, 999)
  return now.getTime()
}

const startOfDayTimestamp = getStartOfDayTimestamp()
const endOfDayTimestamp = getEndOfDayTimestamp()

queryItems.value.start_time = formatTimestamp(startOfDayTimestamp)
queryItems.value.end_time = formatTimestamp(endOfDayTimestamp)

const datetimeRange = ref([startOfDayTimestamp, endOfDayTimestamp])
const handleDateRangeChange = (value) => {
  if (value == null) {
    queryItems.value.start_time = null
    queryItems.value.end_time = null
  } else {
    queryItems.value.start_time = formatTimestamp(value[0])
    queryItems.value.end_time = formatTimestamp(value[1])
  }
}

const methodOptions = [
  {
    label: 'GET',
    value: 'GET',
  },
  {
    label: 'POST',
    value: 'POST',
  },
  {
    label: 'DELETE',
    value: 'DELETE',
  },
]

const columns = [
  {
    title: () => t('system.auditlog.col_username'),
    key: 'username',
    width: 'auto',
    align: 'center',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_summary'),
    key: 'summary',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_module'),
    key: 'module',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_method'),
    key: 'method',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_path'),
    key: 'path',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_status'),
    key: 'status',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_request_id'),
    key: 'request_id',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_response_time'),
    key: 'response_time',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
  {
    title: () => t('system.auditlog.col_created_at'),
    key: 'created_at',
    align: 'center',
    width: 'auto',
    ellipsis: { tooltip: true },
  },
]
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage>
    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getAuditLogList"
    >
      <template #queryBar>
        <QueryBarItem :label="$t('system.auditlog.query_username')" :label-width="70">
          <NInput
            v-model:value="queryItems.username"
            clearable
            type="text"
            :placeholder="$t('system.auditlog.placeholder_username')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_module')" :label-width="70">
          <NInput
            v-model:value="queryItems.module"
            clearable
            type="text"
            :placeholder="$t('system.auditlog.placeholder_module')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_summary')" :label-width="70">
          <NInput
            v-model:value="queryItems.summary"
            clearable
            type="text"
            :placeholder="$t('system.auditlog.placeholder_summary')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_method')" :label-width="70">
          <NSelect
            v-model:value="queryItems.method"
            style="width: 180px"
            :options="methodOptions"
            clearable
            :placeholder="$t('system.auditlog.placeholder_method')"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_path')" :label-width="70">
          <NInput
            v-model:value="queryItems.path"
            clearable
            type="text"
            :placeholder="$t('system.auditlog.placeholder_path')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_status')" :label-width="60">
          <NInput
            v-model:value="queryItems.status"
            clearable
            type="text"
            :placeholder="$t('system.auditlog.placeholder_status')"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem :label="$t('system.auditlog.query_time')" :label-width="70">
          <NDatePicker
            v-model:value="datetimeRange"
            type="datetimerange"
            clearable
            :placeholder="$t('system.auditlog.placeholder_time')"
            @update:value="handleDateRangeChange"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
