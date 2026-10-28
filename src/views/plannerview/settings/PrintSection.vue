<script setup>
import { useI18n } from 'vue-i18n'
import PrimaryButton from '@/components/button/PrimaryButton.vue'
import HintText from '@/components/display/HintText.vue'
import CheckboxField from '@/components/input/CheckboxField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { usePdf } from '@/composables/usePdf'
import { usePlanner } from '@/composables/usePlanner'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()
const { plan } = usePlanner()
const pdf = usePdf()

const PAPERS = [{ value: 'A4', label: 'DIN A4' }, { value: 'A3', label: 'DIN A3' }]
const PARTS = [['overview', 'uebersicht_zuschnitt'], ['front', 'verlegeplan_vorne_1_1'], ['back', 'routing_hinten_1_1']]
</script>

<template>
  <SettingsSection :title="t('n6_druckvorlage')">
    <SegmentedControl v-model="settings.paper" :options="PAPERS" />
    <div class="flex flex-wrap gap-x-4 gap-y-1">
      <CheckboxField v-for="[value, key] in PARTS" :key="value" v-model="settings.parts" :value="value" :label="t(key)" />
    </div>
    <PrimaryButton full-width class="!py-2.5 font-semibold" :disabled="!plan || pdf.busy.value || !settings.parts.length" @click="pdf.download">
      {{ pdf.busy.value ? t('pdf_wird_erstellt') : t('pdf_herunterladen_paper', { paper: settings.paper }) }}
    </PrimaryButton>
    <HintText>{{ t('mit_tatsaechliche_groesse_100_drucken') }}</HintText>
  </SettingsSection>
</template>
