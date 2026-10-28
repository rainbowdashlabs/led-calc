<script setup>
/** A numbered block of the settings sidebar. */
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <section class="space-y-3">
    <h2 class="text-sm font-semibold text-zinc-300">{{ title }}</h2>
    <slot />
  </section>
</template>
