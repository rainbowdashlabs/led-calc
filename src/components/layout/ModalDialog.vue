<script setup>
import BaseCard from '@/components/container/BaseCard.vue'

/** Centered dialog over a dimmed backdrop; clicking the backdrop closes it. */
defineProps({ title: { type: String, required: true } })
const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true" @mousedown.self="emit('close')">
      <BaseCard class="w-full max-w-lg space-y-3 bg-zinc-900 !p-4">
        <h3 class="font-semibold">{{ title }}</h3>
        <slot />
      </BaseCard>
    </div>
  </Teleport>
</template>
