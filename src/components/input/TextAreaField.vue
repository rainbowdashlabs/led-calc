<script setup>
import FieldLabel from './FieldLabel.vue'

const model = defineModel({ type: String })
defineProps({ label: { type: String, required: true }, rows: { type: Number, default: 2 } })
</script>

<template>
  <div>
    <FieldLabel>{{ label }}</FieldLabel>
    <textarea
      v-model="model"
      :rows="rows"
      class="w-full resize-y rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/60 focus:outline-none"
    />
  </div>
</template>
