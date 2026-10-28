<script setup>
/** The shape every button of the app shares; variants only add colours. */
defineProps({
  compact: { type: Boolean, default: false },
  fullWidth: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['click'])
</script>

<template>
  <button
    type="button"
    :disabled="disabled"
    class="inline-flex items-center justify-center gap-1 rounded-md font-medium whitespace-nowrap transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100"
    :class="[compact ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm', fullWidth ? 'w-full' : '']"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>
