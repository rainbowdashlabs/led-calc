<script setup>
import { useI18n } from 'vue-i18n'
import PrimaryButton from '@/components/button/PrimaryButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import HintText from '@/components/display/HintText.vue'
import CheckboxField from '@/components/input/CheckboxField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import OptionGroup from '@/components/layout/OptionGroup.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { useExport } from '@/composables/useExport'
import { usePlanner } from '@/composables/usePlanner'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()
const { plan } = usePlanner()
const { busy, downloadPdf, downloadDxf } = useExport()

const PAPERS = [{ value: 'A4', label: 'DIN A4' }, { value: 'A3', label: 'DIN A3' }]
const PARTS = [['overview', 'uebersicht_zuschnitt'], ['front', 'verlegeplan_vorne_1_1'], ['back', 'routing_hinten_1_1']]
</script>

<template>
  <SettingsSection :title="t('n6_druckvorlage')">
    <SegmentedControl v-model="settings.paper" :options="PAPERS" />
    <div class="flex flex-wrap gap-x-4 gap-y-1">
      <CheckboxField v-for="[value, key] in PARTS" :key="value" v-model="settings.parts" :value="value" :label="t(key)" />
    </div>
    <PrimaryButton full-width class="!py-2.5 font-semibold" :disabled="!plan || busy.pdf || !settings.parts.length" @click="downloadPdf">
      {{ busy.pdf ? t('pdf_wird_erstellt') : t('pdf_herunterladen_paper', { paper: settings.paper }) }}
    </PrimaryButton>
    <HintText>{{ t('mit_tatsaechliche_groesse_100_drucken') }}</HintText>

    <OptionGroup>
      <SecondaryButton full-width :disabled="!plan || busy.dxf" @click="downloadDxf">
        {{ busy.dxf ? t('dxf_wird_erstellt') : t('dxf_herunterladen') }}
      </SecondaryButton>
      <HintText>{{ t('dxf_hinweis') }}</HintText>
    </OptionGroup>
  </SettingsSection>
</template>
