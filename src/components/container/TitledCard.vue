<script setup>
import BaseCard from './BaseCard.vue'

/** Card with a title bar; the body is not padded (tables fill it edge to edge). */
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <BaseCard :padded="false">
    <h3 class="border-b border-zinc-800 px-3 py-2 text-sm font-semibold">{{ title }}</h3>
    <slot />
  </BaseCard>
</template>
