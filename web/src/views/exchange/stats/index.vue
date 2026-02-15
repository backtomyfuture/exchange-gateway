<script setup>
import { onMounted, ref } from 'vue'
import {
  NStatistic,
  NCard,
  NGrid,
  NGi,
  NProgress,
  NSpace,
  NButton,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: '使用统计' })

const stats = ref({
  total_count: 0,
  success_count: 0,
  failed_count: 0,
  success_rate: 0,
  today_count: 0,
  active_accounts: 0,
  active_api_keys: 0,
})
const loading = ref(false)

onMounted(() => {
  loadStats()
})

async function loadStats() {
  loading.value = true
  try {
    const res = await api.getExchangeStats()
    if (res.code === 200) {
      stats.value = res.data || {}
    }
  } catch (err) {
    console.error('加载统计失败', err)
  } finally {
    loading.value = false
  }
}

const columns = [
    { title: '日期', key: 'date' },
    { title: '总请求', key: 'total' },
    { title: '成功', key: 'success' },
    { title: '失败', key: 'failed' },
]
</script>

<template>
  <CommonPage show-footer title="使用统计">
    <template #action>
      <NButton type="primary" :loading="loading" @click="loadStats">
        <TheIcon icon="mdi:refresh" :size="18" class="mr-5" />刷新
      </NButton>
    </template>

    <!-- 统计卡片 -->
    <NGrid :cols="4" :x-gap="16" :y-gap="16">
      <NGi>
        <NCard>
          <NStatistic label="总请求数" :value="stats.total_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:email-multiple" :size="24" style="color: #2080f0" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="成功请求" :value="stats.success_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:check-circle" :size="24" style="color: #18a058" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="失败请求" :value="stats.failed_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:close-circle" :size="24" style="color: #d03050" />
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



    <NGrid :cols="3" :x-gap="16" :y-gap="16" style="margin-top: 16px">
      <NGi>
        <NCard>
          <NStatistic label="今日请求" :value="stats.today_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:calendar-today" :size="24" style="color: #f0a020" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="活跃账户" :value="stats.active_accounts || 0">
            <template #prefix>
              <TheIcon icon="mdi:account-check" :size="24" style="color: #2080f0" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="有效密钥" :value="stats.active_api_keys || 0">
            <template #prefix>
              <TheIcon icon="mdi:key-variant" :size="24" style="color: #18a058" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
    </NGrid>

    <NCard title="每日趋势 (最近30天)" style="margin-top: 16px" size="small">
        <n-data-table
            :columns="columns"
            :data="stats.daily_stats || []"
            :bordered="false"
            size="small"
            :max-height="400"
        />
    </NCard>
  </CommonPage>
</template>
