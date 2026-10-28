<script setup>
/** Thin progress bar; `fraction` is 0..1. */
defineProps({
  fraction: { type: Number, required: true },
  glow: { type: Boolean, default: false },
})
</script>

<template>
  <div class="h-full overflow-hidden rounded-full bg-zinc-800/60">
    <div
      class="h-full rounded-full bg-pink-500 transition-all duration-150"
      :class="glow ? 'shadow-[0_0_8px_rgba(255,60,172,0.9)]' : ''"
      :style="{ width: `${Math.round(fraction * 100)}%` }"
    />
  </div>
</template>
