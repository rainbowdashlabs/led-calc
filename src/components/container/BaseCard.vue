<script setup>
defineProps({ padded: { type: Boolean, default: true } })
</script>

<template>
  <div class="rounded-xl border border-zinc-800 bg-zinc-900/70" :class="padded ? 'p-3' : 'overflow-hidden'">
    <slot />
  </div>
</template>
