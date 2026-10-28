<script setup>
/** Styled native input; all attributes are passed through. */
const model = defineModel({ type: [String, Number] })
</script>

<template>
  <input
    v-model="model"
    class="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/60 focus:outline-none"
  />
</template>
