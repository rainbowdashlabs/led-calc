<script setup>
import BaseButton from './BaseButton.vue'

/** Square button with a one-character symbol; `label` is its accessible name. */
defineProps({ label: { type: String, required: true } })
</script>

<template>
  <BaseButton compact class="h-6 w-6 !px-0 border border-zinc-700 text-zinc-300 hover:border-zinc-500" :title="label" :aria-label="label"><slot /></BaseButton>
</template>
