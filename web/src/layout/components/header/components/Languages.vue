<template>
  <n-dropdown :options="options" @select="handleChangeLocale">
    <n-icon mr-20 size="18" style="cursor: pointer">
      <icon-mdi:globe />
    </n-icon>
  </n-dropdown>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/store'

const store = useAppStore()
const { availableLocales, t } = useI18n()

const options = computed(() => {
  return availableLocales.map((locale) => ({
    label: t('lang', 1, { locale }),
    key: locale,
  }))
})

const handleChangeLocale = (value) => {
  store.setLocale(value)
  window.location.reload()
}
</script>
