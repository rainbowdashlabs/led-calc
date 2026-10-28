<script setup>
import LanguageToggle from '@/components/input/LanguageToggle.vue'
import AppTitle from './AppTitle.vue'

/** Slim top bar on phones and tablets: app name and language. */
</script>

<template>
  <header class="sticky top-0 z-30 flex items-center justify-between border-b border-zinc-800 bg-zinc-950/90 px-3 py-2 pt-[calc(0.5rem+env(safe-area-inset-top))] backdrop-blur">
    <AppTitle class="text-lg" />
    <LanguageToggle />
  </header>
</template>
