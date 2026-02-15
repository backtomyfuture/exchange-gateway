<template>
  <router-link h-60 f-c-c to="/">
    <img :src="logo" style="height: 36px; width: 36px; object-fit: cover; object-position: left;" />
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
      {{ title }}
    </h2>
  </router-link>
</template>

<script setup>
import { useAppStore } from '@/store'
import logo from '@/assets/images/swallow_icon.png'
const title = import.meta.env.VITE_TITLE

const appStore = useAppStore()
</script>
