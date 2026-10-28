<script setup>
import FieldLabel from './FieldLabel.vue'

const model = defineModel({ type: String })
defineProps({ label: { type: String, default: '' }, inline: { type: Boolean, default: false } })
</script>

<template>
  <label v-if="inline" class="inline-flex items-center gap-1 text-xs text-zinc-400">
    {{ label }}
    <input v-model="model" type="color" class="h-6 w-8 rounded border border-zinc-700 bg-zinc-900" />
  </label>
  <div v-else>
    <FieldLabel>{{ label }}</FieldLabel>
    <input v-model="model" type="color" class="h-[34px] w-full rounded-md border border-zinc-700 bg-zinc-900" />
  </div>
</template>
