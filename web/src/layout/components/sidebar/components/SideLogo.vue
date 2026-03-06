<template>
  <router-link h-60 f-c-c to="/">
    <img :src="logo" style="height: 36px; width: 36px; object-fit: contain;" />
    <h2
      v-show="!appStore.collapsed"
      ml-2
      mr-8
      max-w-150
      flex-shrink-0
      text-16
      font-bold
      color-primary
    >
      {{ $t('app_name') }}
    </h2>
  </router-link>
</template>

<script setup>
import { useAppStore } from '@/store'
import logo from '@/assets/svg/logo.svg'

const appStore = useAppStore()
</script>
