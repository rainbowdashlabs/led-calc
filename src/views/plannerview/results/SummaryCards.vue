<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import StatCard from '@/components/display/StatCard.vue'
import { useFormat } from '@/composables/useFormat'
import { usePlanner } from '@/composables/usePlanner'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { fmtLen } = useFormat()
const { plan } = usePlanner()
const { settings } = useSettings()

const summary = computed(() => plan.value.summary)
const continuous = computed(() => settings.connection === 'strip')
// every strip link passes the plate twice (out and back in)
const passCount = computed(() => plan.value.links.filter((l) => l.kind === 'strip').length * 2)
const passLength = computed(() => passCount.value * (settings.plateThickness + settings.passExtra))
</script>

<template>
  <div class="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-4">
    <StatCard :label="t('streifen_gesamt_zu_kaufen')" :value="fmtLen(summary.strip_cut_total)" accent>
      {{ t('vorne_hinten_durchfuehrungen_auf_raster') }}
    </StatCard>
    <StatCard :label="t('sichtbar_vorne')" :value="fmtLen(summary.front)">
      {{ t('n_stuecke', { n: summary.pieces }) }}
    </StatCard>
    <StatCard :label="t('hinter_der_platte')" :value="fmtLen(continuous ? summary.back_strip : summary.cable)">
      <template v-if="continuous">
        {{ t('streifen_davon_a_fuer_n', { a: fmtLen(passLength), n: passCount }) }}<template v-if="summary.cable">{{ t('c_kabel', { c: fmtLen(summary.cable) }) }}</template>
      </template>
      <template v-else>{{ t('kabel_inkl_reserve') }}</template>
    </StatCard>
    <StatCard :label="t('bohrungen')" :value="summary.holes">
      {{ t('d_mm_n_uebergaenge', { d: settings.holeDiameter, n: summary.transitions }) }}
    </StatCard>
  </div>
</template>
