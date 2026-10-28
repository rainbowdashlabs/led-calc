<script setup>
import BaseCard from '@/components/container/BaseCard.vue'

/** A key figure: label, big value and an optional explanation below. */
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  accent: { type: Boolean, default: false },
})
</script>

<template>
  <BaseCard>
    <div class="text-xs text-zinc-500">{{ label }}</div>
    <div class="text-2xl font-bold" :class="accent ? 'text-pink-400' : ''">{{ value }}</div>
    <div class="text-xs text-zinc-500"><slot /></div>
  </BaseCard>
</template>
