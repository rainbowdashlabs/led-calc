<script setup>
/** A row of mutually exclusive buttons. `options`: [{ value, label, disabled? }]. */
const model = defineModel({ type: [String, Number] })
defineProps({
  options: { type: Array, required: true },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="flex rounded-lg border border-zinc-700 bg-zinc-900 p-0.5" :class="compact ? 'text-xs' : 'text-sm'" role="radiogroup">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="model === option.value"
      :disabled="option.disabled"
      class="flex-1 rounded-md px-2 py-1 transition disabled:cursor-not-allowed disabled:opacity-40"
      :class="model === option.value ? 'bg-pink-600 text-white shadow' : 'text-zinc-400 hover:text-zinc-200'"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>
