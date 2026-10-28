<script setup>
import { useI18n } from 'vue-i18n'
import BaseCard from '@/components/container/BaseCard.vue'
import { usePlanner } from '@/composables/usePlanner'

const { t } = useI18n()
const { plan } = usePlanner()
</script>

<template>
  <BaseCard v-if="plan.cut" class="text-sm">
    <h3 class="mb-1 font-semibold">{{ plan.cut.mode === 'groove' ? t('nut_fraesen') : t('durchbruch') }}</h3>
    <p class="text-zinc-400">
      {{ t('kanalbreite_w_mm', { w: plan.cut.width }) }}{{ plan.cut.mode === 'groove'
        ? t('tiefe_d_mm', { d: plan.cut.depth })
        : t('n_lose_teile_gesichert_mit', { n: plan.cut.islands, b: plan.cut.bridges.length }) }}
    </p>
  </BaseCard>
</template>
