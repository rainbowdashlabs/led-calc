<script setup>
import { useI18n } from 'vue-i18n'
import ColorField from '@/components/input/ColorField.vue'
import NumberField from '@/components/input/NumberField.vue'
import FieldGrid from '@/components/layout/FieldGrid.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { usePreviewState } from '@/composables/usePreviewState'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()
const preview = usePreviewState()
</script>

<template>
  <SettingsSection :title="t('n3_led_streifen')">
    <FieldGrid>
      <NumberField v-model="settings.stripWidth" :label="t('breite_dicke_mm')" :min="2" :step="0.5" />
      <NumberField v-model="settings.bendRadiusCm" :label="t('min_biegeradius_90_cm')" :min="0" :step="0.1" :hint="t('gilt_vorne_und_hinter_der')" />
      <NumberField v-model="settings.cutUnit" :label="t('schnittraster_mm')" :min="0" />
      <NumberField v-model="settings.rollLengthM" :label="t('rollenlaenge_m')" :min="0.5" :step="0.5" />
      <NumberField v-model="settings.pieceAllowance" :label="t('zugabe_je_zuschnitt_mm')" :min="0" />
      <ColorField v-model="preview.neonColor" :label="t('farbe_vorschau')" />
    </FieldGrid>
  </SettingsSection>
</template>
