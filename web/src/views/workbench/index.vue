<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <!-- 头部欢迎区 -->
      <n-card rounded-10 class="mb-15" :bordered="false" content-style="padding: 0;">
         <div class="welcome-header relative overflow-hidden rounded-10 p-20">
             <div class="relative z-10 flex items-center justify-between">
                <div flex items-center>
                    <n-avatar
                        round
                        :size="64"
                        :src="userStore.avatar"
                        class="border-2 border-white shadow-sm"
                    />
                    <div ml-15>
                    <p text-20 font-bold text-white>
                        {{ $t('workbench.greeting_text', { username: userStore.name, greeting: greeting }) }}
                    </p>
                    <p mt-5 text-14 text-white op-80>{{ $t('workbench.subtitle') }}</p>
                    </div>
                </div>
                 <div class="hidden md:block text-white text-right op-80">
                    <div text-24 font-mono>{{ currentTime }}</div>
                    <div text-12>{{ currentDate }}</div>
                </div>
             </div>
             <!-- 背景装饰 -->
             <div class="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-blue-500 to-indigo-600 opacity-90"></div>
             <div class="absolute -right-10 -bottom-20 w-60 h-60 bg-white op-10 rounded-full blur-3xl"></div>
             <div class="absolute left-20 -top-20 w-40 h-40 bg-white op-10 rounded-full blur-2xl"></div>
         </div>
      </n-card>

      <!-- 核心指标卡片 -->
      <n-grid :x-gap="15" :y-gap="15" cols="1 s:2" responsive="screen">
        <!-- Exchange 指标 -->
        <n-gi>
            <n-card size="small" rounded-10 hoverable>
                <div class="flex flex-col">
                    <span class="text-gray-500 text-12">{{ $t('workbench.today_send') }}</span>
                    <div class="flex items-end mt-2">
                        <span class="text-28 font-bold">{{ stats.today_stats?.today_count || 0 }}</span>
                        <span class="ml-2 mb-1 text-xs" :class="getSuccessRateColor(stats.today_stats?.success_rate)">
                             {{ stats.today_stats?.success_rate || 0 }}% {{ $t('workbench.success_rate') }}
                        </span>
                    </div>
                     <div class="mt-3 flex items-center text-gray-400 text-xs">
                         <TheIcon icon="material-symbols:mail-outline" class="mr-1" />
                         <span>{{ $t('workbench.total_send') }}: {{ stats.today_stats?.total_count || 0 }}</span>
                    </div>
                </div>
            </n-card>
        </n-gi>
         <n-gi>
            <n-card size="small" rounded-10 hoverable>
                <div class="flex flex-col">
                    <span class="text-gray-500 text-12">{{ $t('workbench.active_accounts_api') }}</span>
                    <div class="flex items-end mt-2">
                         <span class="text-28 font-bold text-primary">{{ stats.account_stats?.active || 0 }}</span>
                         <span class="ml-2 mb-1 text-gray-400 text-xs">/ {{ stats.account_stats?.total || 0 }} {{ $t('workbench.accounts') }}</span>
                    </div>
                    <div class="mt-3 flex items-center text-gray-400 text-xs">
                        <TheIcon icon="material-symbols:key-outline" class="mr-1" />
                        <span>{{ $t('workbench.active_api_keys') }}: {{ stats.today_stats?.active_api_keys || 0 }}</span>
                    </div>
                </div>
            </n-card>
        </n-gi>
      </n-grid>

      <!-- 主要内容区 (双栏布局) -->
      <n-grid cols="1" mt-15>
        <!-- 左侧：邮件日志 -->
         <n-gi>
            <n-card :title="$t('workbench.send_records')" size="small" segmented rounded-10 class="h-full">
                <template #header-extra>
                   <n-button text type="primary" size="tiny" @click="$router.push('/exchange/logs')">{{ $t('workbench.view_more') }}</n-button>
                </template>
                <div v-if="!stats.recent_logs?.length" class="flex flex-col items-center justify-center py-10 op-60">
                     <TheIcon icon="material-symbols:inbox-customize-outline" :size="40" class="mb-2 text-gray-300"/>
                     <span class="text-12">{{ $t('workbench.no_records') }}</span>
                </div>
                 <n-list v-else hoverable clickable>
                    <n-list-item v-for="log in stats.recent_logs" :key="log.id">
                        <div class="flex items-center justify-between">
                             <div class="flex items-center gap-3 overflow-hidden">
                                 <div class="flex-shrink-0">
                                      <TheIcon 
                                        :icon="log.status === 'success' ? 'material-symbols:check-circle-outline' : 'material-symbols:error-outline'" 
                                        :size="20" 
                                        :class="log.status === 'success' ? 'text-green-500' : 'text-red-500'" 
                                      />
                                 </div>
                                 <div class="flex flex-col overflow-hidden">
                                     <span class="text-13 font-medium truncate">{{ log.subject || $t('workbench.no_subject') }}</span>
                                     <span class="text-12 text-gray-400 truncate">To: {{ (log.recipients || []).join(', ') }}</span>
                                 </div>
                             </div>
                             <div class="text-12 text-gray-400 whitespace-nowrap ml-2">
                                 {{ formatTimeAgo(log.created_at) }}
                             </div>
                        </div>
                    </n-list-item>
                 </n-list>
            </n-card>
         </n-gi>
      </n-grid>
      
      <!-- 快捷入口 -->
      <n-grid :x-gap="15" :y-gap="15" cols="2 s:4" responsive="screen" mt-15>
          <n-gi v-for="action in quickActions" :key="action.path">
              <n-card size="small" hoverable class="cursor-pointer text-center group" @click="$router.push(action.path)">
                   <div class="py-2 flex flex-col items-center justify-center">
                       <div class="w-10 h-10 rounded-full bg-gray-50 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-300" :class="action.bgClass">
                            <TheIcon :icon="action.icon" :size="20" :class="action.textClass" />
                       </div>
                       <span class="text-13 text-gray-600">{{ action.title }}</span>
                   </div>
              </n-card>
          </n-gi>
      </n-grid>

    </div>
  </AppPage>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import api from '@/api'
import { formatDate } from '@/utils'
import TheIcon from '@/components/icon/TheIcon.vue'

const { t, locale } = useI18n()

dayjs.extend(relativeTime)
dayjs.locale(locale.value === 'en' ? 'en' : 'zh-cn')

const userStore = useUserStore()
const $router = useRouter()
const stats = ref({})
const currentTime = ref('')
const currentDate = ref('')
let timer = null

// 问候语
const greeting = computed(() => {
    const hour = new Date().getHours()
    if (hour < 6) return t('workbench.greeting_late_night')
    if (hour < 9) return t('workbench.greeting_morning')
    if (hour < 12) return t('workbench.greeting_forenoon')
    if (hour < 14) return t('workbench.greeting_noon')
    if (hour < 17) return t('workbench.greeting_afternoon')
    if (hour < 19) return t('workbench.greeting_evening')
    return t('workbench.greeting_night')
})

// 快捷入口配置
const quickActions = computed(() => [
    { title: t('workbench.quick_manage_accounts'), path: '/exchange/accounts', icon: 'material-symbols:mail-outline', bgClass: 'group-hover:bg-indigo-100', textClass: 'text-indigo-500' },
    { title: t('workbench.quick_manage_templates'), path: '/exchange/templates', icon: 'material-symbols:article-outline', bgClass: 'group-hover:bg-green-100', textClass: 'text-green-500' },
    { title: t('workbench.quick_view_logs'), path: '/exchange/logs', icon: 'material-symbols:history', bgClass: 'group-hover:bg-blue-100', textClass: 'text-blue-500' },
    { title: t('workbench.quick_api_docs'), path: '/developer/index', icon: 'material-symbols:code', bgClass: 'group-hover:bg-orange-100', textClass: 'text-orange-500' },
])

onMounted(async () => {
    loadData()
    updateTime()
    timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
    if (timer) clearInterval(timer)
})

function updateTime() {
    const now = new Date()
    const dateLoc = locale.value === 'en' ? 'en-US' : 'zh-CN'
    currentTime.value = now.toLocaleTimeString(dateLoc, { hour12: false })
    currentDate.value = now.toLocaleDateString(dateLoc, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}

async function loadData() {
    try {
        const res = await api.getDashboardData()
        if (res.code === 200) {
            stats.value = res.data
        }
    } catch (e) {
        console.error("Failed to load dashboard data", e)
    }
}

function getSuccessRateColor(rate) {
    if (!rate && rate !== 0) return 'text-gray-400'
    if (rate >= 95) return 'text-green-500'
    if (rate >= 80) return 'text-yellow-500'
    return 'text-red-500'
}


function formatTimeAgo(dateStr) {
    if (!dateStr) return ''
    try {
        return dayjs(dateStr).fromNow().replace(' ', '')
    } catch (e) {
        return formatDate(dateStr)
    }
}
</script>

<style scoped>
</style>
