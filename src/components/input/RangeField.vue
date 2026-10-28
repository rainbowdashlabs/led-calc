<script setup>
const model = defineModel({ type: Number })
defineProps({
  min: { type: Number, required: true },
  max: { type: Number, required: true },
  step: { type: Number, default: 1 },
  label: { type: String, default: '' },
})
</script>

<template>
  <input v-model.number="model" type="range" :min="min" :max="max" :step="step" :aria-label="label || undefined" class="w-full accent-pink-500" />
</template>
