<script setup>
/** One entry of a legend; `shape`: 'line' | 'dashed' | 'ring' | 'dashed-ring'. */
defineProps({
  shape: { type: String, required: true },
  color: { type: String, required: true },
})
</script>

<template>
  <span class="inline-flex items-center gap-1">
    <i
      class="inline-block"
      :class="{
        'h-2 w-4 rounded': shape === 'line',
        'h-0 w-4 border-t-2 border-dashed': shape === 'dashed',
        'h-2.5 w-2.5 rounded-full border-2': shape === 'ring',
        'h-2.5 w-2.5 rounded-full border-2 border-dashed': shape === 'dashed-ring',
      }"
      :style="shape === 'line' ? { background: color } : { borderColor: color }"
    />
    <slot />
  </span>
</template>
