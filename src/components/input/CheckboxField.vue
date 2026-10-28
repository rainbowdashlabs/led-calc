<script setup>
const model = defineModel({ type: [Boolean, Array] })
defineProps({ label: { type: String, required: true }, value: { type: String, default: undefined } })
</script>

<template>
  <label class="inline-flex items-center gap-2 text-sm text-zinc-200">
    <input v-model="model" type="checkbox" :value="value" class="accent-pink-500" />
    {{ label }}
  </label>
</template>
