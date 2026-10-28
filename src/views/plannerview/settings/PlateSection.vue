<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import HintText from '@/components/display/HintText.vue'
import NumberField from '@/components/input/NumberField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import SelectField from '@/components/input/SelectField.vue'
import FieldGrid from '@/components/layout/FieldGrid.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()

const connections = computed(() => [
  { value: 'strip', label: t('streifen_durchgehend') },
  { value: 'cable', label: t('einzelstuecke_kabel') },
])
const FEEDS = {
  'bottom-left': 'unten_links', 'bottom-center': 'unten_mittig', 'bottom-right': 'unten_rechts',
  left: 'links_mittig', right: 'rechts_mittig',
  'top-left': 'oben_links', 'top-center': 'oben_mittig', 'top-right': 'oben_rechts',
}
const feeds = computed(() => Object.entries(FEEDS).map(([value, key]) => ({ value, label: t(key) })))
</script>

<template>
  <SettingsSection :title="t('n4_platte_routing')">
    <SegmentedControl v-model="settings.connection" :options="connections" />
    <HintText>{{ settings.connection === 'strip' ? t('zwischen_zwei_stuecken_taucht_der') : t('jedes_stueck_wird_einzeln_abgeschnitten') }}</HintText>
    <FieldGrid>
      <NumberField v-model="settings.marginCm" :label="t('rand_um_schrift_cm')" :min="0" :step="0.5" />
      <NumberField v-model="settings.plateCorner" :label="t('eckenradius_mm')" :min="0" />
      <NumberField v-model="settings.plateThickness" :label="t('plattenstaerke_mm')" :min="1" :step="0.5" />
      <NumberField v-model="settings.holeDiameter" :label="t('bohrung_mm')" :min="3" :step="0.5" />
      <NumberField v-if="settings.connection === 'strip'" v-model="settings.passExtra" :label="t('zugabe_je_durchfuehrung_mm')" :min="0" />
      <NumberField v-else v-model="settings.cableReserve" :label="t('kabelreserve_mm')" :min="0" :step="5" />
      <SelectField v-model="settings.feed" :label="t('einspeisung')" :options="feeds" />
    </FieldGrid>
  </SettingsSection>
</template>
