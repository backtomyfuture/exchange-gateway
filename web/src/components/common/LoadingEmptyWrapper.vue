<template>
  <div v-if="reloadFlag" class="relative">
    <slot></slot>
    <div v-show="showPlaceholder" class="absolute-lt h-full w-full" :class="placeholderClass">
      <div v-show="loading" class="absolute-center">
        <n-spin :show="true" :size="loadingSize" />
      </div>
      <div v-show="isEmpty" class="absolute-center">
        <div class="relative">
          <icon-custom-no-data :class="iconClass" />
          <p class="absolute-lb w-full text-center" :class="descClass">{{ t('common.no_data') }}</p>
        </div>
      </div>
      <div v-show="!network" class="absolute-center">
        <div
          class="relative"
          :class="{ 'cursor-pointer': showNetworkReload }"
          @click="handleReload"
        >
          <icon-custom-network-error :class="iconClass" />
          <p class="absolute-lb w-full text-center" :class="descClass">{{ networkErrorDesc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

defineOptions({ name: 'LoadingEmptyWrapper' })

const { t } = useI18n()

const props = {
  loading: false,
  empty: false,
  loadingSize: 'medium',
  placeholderClass: 'bg-white dark:bg-dark transition-background-color duration-300 ease-in-out',
  iconClass: 'text-320px text-primary',
  descClass: 'text-16px text-#666',
  showNetworkReload: false,
}

// 网络状态
const network = ref(window.navigator.onLine)
const reloadFlag = ref(true)

// 数据是否为空
const isEmpty = computed(() => props.empty && !props.loading && network.value)

const showPlaceholder = computed(() => props.loading || isEmpty.value || !network.value)

const networkErrorDesc = computed(() =>
  props.showNetworkReload ? `${t('common.network_error')}, ${t('common.network_retry')}` : t('common.network_error'),
)

function handleReload() {
  if (!props.showNetworkReload) return
  reloadFlag.value = false
  nextTick(() => {
    reloadFlag.value = true
  })
}

const stopHandle = watch(
  () => props.loading,
  (newValue) => {
    // 结束加载判断一下网络状态
    if (!newValue) {
      network.value = window.navigator.onLine
    }
  },
)

onUnmounted(() => {
  stopHandle()
})
</script>

<style scoped></style>
