<script setup>
defineProps({ columns: { type: Number, default: 2 } })
</script>

<template>
  <div class="grid gap-2" :class="columns === 3 ? 'grid-cols-3' : 'grid-cols-2'"><slot /></div>
</template>
