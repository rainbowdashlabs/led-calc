<script setup>
import ErrorCard from '@/components/container/ErrorCard.vue'
import InfoCard from '@/components/container/InfoCard.vue'
import WarningCard from '@/components/container/WarningCard.vue'
import { useNotice } from '@/composables/useNotice'
import { usePlanner } from '@/composables/usePlanner'

const { notice } = useNotice()
const { plan, error } = usePlanner()
</script>

<template>
  <InfoCard v-if="notice">{{ notice }}</InfoCard>
  <ErrorCard v-if="error">{{ error }}</ErrorCard>
  <WarningCard v-if="plan.warnings.length" class="space-y-1">
    <p v-for="(warning, i) in plan.warnings" :key="i">⚠ {{ warning }}</p>
  </WarningCard>
</template>
