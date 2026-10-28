<script setup>
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()
</script>

<template>
  <h1 class="font-bold tracking-tight">
    <span class="text-pink-400 drop-shadow-[0_0_8px_rgba(255,60,172,0.8)]">LED-Neon</span> {{ locale === 'de' ? 'Planer' : 'Planner' }}
  </h1>
</template>
