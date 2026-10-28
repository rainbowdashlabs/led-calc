<script setup>
/** Opens a file dialog; emits the chosen file. Looks like a SecondaryButton or a link. */
defineProps({
  accept: { type: String, default: '' },
  variant: { type: String, default: 'button' }, // 'button' | 'link'
})
const emit = defineEmits(['select'])

function onChange(event) {
  const file = event.target.files?.[0]
  if (file) emit('select', file)
  event.target.value = ''
}
</script>

<template>
  <label
    class="inline-flex cursor-pointer items-center gap-1"
    :class="variant === 'link'
      ? 'text-xs text-pink-400 hover:text-pink-300'
      : 'rounded-md border border-zinc-700 px-2 py-1 text-xs font-medium text-zinc-300 hover:border-pink-500'"
  >
    <slot />
    <input type="file" :accept="accept" class="hidden" @change="onChange" />
  </label>
</template>
