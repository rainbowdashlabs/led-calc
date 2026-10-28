<script setup>
import FieldLabel from './FieldLabel.vue'

/** Labelled select. `options`: [{ value, label }]. */
const model = defineModel({ type: [String, Number] })
defineProps({
  label: { type: String, default: '' },
  options: { type: Array, required: true },
})
</script>

<template>
  <div>
    <FieldLabel v-if="label">{{ label }}</FieldLabel>
    <select
      v-model="model"
      class="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/60 focus:outline-none"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option>
    </select>
  </div>
</template>
