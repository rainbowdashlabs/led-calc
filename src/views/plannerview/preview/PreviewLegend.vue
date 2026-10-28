<script setup>
import { useI18n } from 'vue-i18n'
import LegendItem from '@/components/display/LegendItem.vue'
import { useFormat } from '@/composables/useFormat'
import { useSettings } from '@/composables/useSettings'

defineProps({ plan: { type: Object, required: true } })
const { t } = useI18n()
const { fmtCm } = useFormat()
const { settings } = useSettings()

const LEGEND = [
  ['dashed', '#f59e0b', 'streifen_hinten'],
  ['dashed', '#38bdf8', 'kabel'],
  ['ring', '#f59e0b', 'nach_hinten'],
  ['ring', '#22c55e', 'nach_vorne'],
  ['ring', '#ef4444', 'zu_eng'],
  ['dashed-ring', '#38bdf8', 'geglaettet'],
]
</script>

<template>
  <div class="flex flex-wrap gap-x-4 gap-y-1 border-t border-zinc-800 px-3 py-2 text-xs text-zinc-400">
    <span>{{ t('platte') }} <b class="text-zinc-200">{{ fmtCm(plan.plate.w) }} × {{ fmtCm(plan.plate.h) }}</b></span>
    <span>{{ t('schrift') }} <b class="text-pink-300">{{ fmtCm(plan.bounds.x1 - plan.bounds.x0) }} × {{ fmtCm(plan.bounds.y1 - plan.bounds.y0) }}</b></span>
    <span>{{ t('zeichenhoehe_h_breite_w', { h: fmtCm(plan.params.cap_height), w: settings.widthPct }) }}</span>
    <span v-if="plan.manual" class="text-pink-300">{{ t('manuell_bearbeitet') }}</span>
    <span class="ml-auto flex flex-wrap gap-x-4 gap-y-1">
      <LegendItem v-for="[shape, color, key] in LEGEND" :key="key" :shape="shape" :color="color">{{ t(key) }}</LegendItem>
    </span>
  </div>
</template>
