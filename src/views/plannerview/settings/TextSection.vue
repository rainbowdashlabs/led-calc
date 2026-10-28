<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FileButton from '@/components/button/FileButton.vue'
import HintText from '@/components/display/HintText.vue'
import FieldLabel from '@/components/input/FieldLabel.vue'
import FontPicker from '@/components/input/FontPicker.vue'
import NumberField from '@/components/input/NumberField.vue'
import RangeField from '@/components/input/RangeField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import TextAreaField from '@/components/input/TextAreaField.vue'
import FieldGrid from '@/components/layout/FieldGrid.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { useFonts } from '@/composables/useFonts'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()
const { base, fonts, customFont, weightInfo, effectiveWeight, setCustomFont } = useFonts()

const alignments = computed(() => [
  { value: 'left', label: t('links') },
  { value: 'center', label: t('mittig') },
  { value: 'right', label: t('rechts') },
])
const weight = computed({
  get: () => effectiveWeight.value,
  set: (value) => { settings.fontWeight = value },
})

async function upload(file) {
  setCustomFont(file.name, new Uint8Array(await file.arrayBuffer()))
  settings.fontId = 'custom'
}
</script>

<template>
  <SettingsSection :title="t('n1_text_schrift')">
    <TextAreaField v-model="settings.text" :label="t('text_mehrzeilig_moeglich')" />

    <div>
      <FieldLabel>{{ t('schriftart') }}</FieldLabel>
      <FontPicker v-model="settings.fontId" :fonts="fonts" :custom="customFont" :sample="settings.text" :base="base" :weight="effectiveWeight" />
      <FileButton variant="link" accept=".ttf,.otf,.jhf" class="mt-1.5" @select="upload">{{ t('eigene_schrift_hochladen_ttf_otf') }}</FileButton>
    </div>

    <div v-if="weightInfo">
      <FieldLabel>
        <span class="flex justify-between">
          <span>
            {{ t('strichstaerke') }}: {{ Math.round(effectiveWeight) }}
            <span v-if="settings.fontWeight === null" class="text-zinc-500">({{ t('auto_kurz') }})</span>
          </span>
          <button v-if="settings.fontWeight !== null" type="button" class="text-pink-400 hover:text-pink-300" @click="settings.fontWeight = null">
            {{ t('auto_kurz') }}
          </button>
        </span>
      </FieldLabel>
      <RangeField v-model="weight" :min="weightInfo.min" :max="weightInfo.max" :step="50" :label="t('strichstaerke')" />
      <HintText>{{ settings.fontWeight === null ? t('strichstaerke_auto') : t('strichstaerke_hint') }}</HintText>
    </div>

    <FieldGrid :columns="3">
      <NumberField v-model="settings.capHeightCm" :label="t('zeichenhoehe_cm')" :min="2" :step="0.5" :hint="t('hoehe_der_grossbuchstaben')" />
      <NumberField v-model="settings.trackingMm" :label="t('zeichenabstand_mm')" :hint="t('zusaetzlicher_abstand_zwischen_den_zeichen')" />
      <NumberField v-model="settings.widthPct" :label="t('zeichenbreite')" :min="40" :max="250" :step="5" :hint="t('zeichen_schmaler_100_oder_breiter')" />
    </FieldGrid>

    <FieldGrid :columns="3">
      <NumberField v-model="settings.lineSpacing" :label="t('zeilenabstand')" :min="0.8" :step="0.1" />
      <div class="col-span-2">
        <FieldLabel>{{ t('ausrichtung') }}</FieldLabel>
        <SegmentedControl v-model="settings.align" :options="alignments" />
      </div>
    </FieldGrid>
  </SettingsSection>
</template>
