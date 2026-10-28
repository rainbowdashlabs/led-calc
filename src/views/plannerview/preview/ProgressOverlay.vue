<script setup>
import ProgressBar from '@/components/display/ProgressBar.vue'

/** Progress bar on top of the preview plus the current step. */
defineProps({
  active: { type: Boolean, required: true },
  fraction: { type: Number, required: true },
  label: { type: String, required: true },
})
</script>

<template>
  <div class="absolute inset-x-0 top-0 z-10 h-1 transition-opacity" :class="active ? 'opacity-100' : 'opacity-0'">
    <ProgressBar :fraction="fraction" glow class="!rounded-none" />
  </div>
  <div v-if="active" class="absolute top-2 right-3 z-10 rounded bg-black/70 px-2 py-0.5 text-[11px] text-pink-300">
    {{ label }} · {{ Math.round(fraction * 100) }} %
  </div>
</template>
