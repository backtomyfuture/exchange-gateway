<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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

defineOptions({ name: 'UsageStats' })

const { t } = useI18n()

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
    { title: () => t('exchange.stats.col_date'), key: 'date' },
    { title: () => t('exchange.stats.col_total'), key: 'total' },
    { title: () => t('exchange.stats.col_success'), key: 'success' },
    { title: () => t('exchange.stats.col_failed'), key: 'failed' },
]
</script>

<template>
  <CommonPage show-footer :title="$t('exchange.stats.title')">
    <template #action>
      <NButton type="primary" :loading="loading" @click="loadStats">
        <TheIcon icon="mdi:refresh" :size="18" class="mr-5" />{{ $t('exchange.stats.btn_refresh') }}
      </NButton>
    </template>

    <!-- 统计卡片 -->
    <NGrid :cols="4" :x-gap="16" :y-gap="16">
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_total')" :value="stats.total_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:email-multiple" :size="24" style="color: #2080f0" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_success')" :value="stats.success_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:check-circle" :size="24" style="color: #18a058" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_failed')" :value="stats.failed_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:close-circle" :size="24" style="color: #d03050" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_success_rate')" :value="stats.success_rate || 0">
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
          <NStatistic :label="$t('exchange.stats.stat_today')" :value="stats.today_count || 0">
            <template #prefix>
              <TheIcon icon="mdi:calendar-today" :size="24" style="color: #f0a020" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_active_accounts')" :value="stats.active_accounts || 0">
            <template #prefix>
              <TheIcon icon="mdi:account-check" :size="24" style="color: #2080f0" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic :label="$t('exchange.stats.stat_active_keys')" :value="stats.active_api_keys || 0">
            <template #prefix>
              <TheIcon icon="mdi:key-variant" :size="24" style="color: #18a058" />
            </template>
          </NStatistic>
        </NCard>
      </NGi>
    </NGrid>

    <NCard :title="$t('exchange.stats.daily_trend')" style="margin-top: 16px" size="small">
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
