<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import HintText from '@/components/display/HintText.vue'
import CheckboxField from '@/components/input/CheckboxField.vue'
import NumberField from '@/components/input/NumberField.vue'
import SelectField from '@/components/input/SelectField.vue'
import FieldGrid from '@/components/layout/FieldGrid.vue'
import OptionGroup from '@/components/layout/OptionGroup.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()

const corners = computed(() => [
  { value: 'round', label: t('gebogen_biegeradius') },
  { value: 'butt', label: t('eckig_4_stuecke') },
])
const cutModes = computed(() => [
  { value: 'none', label: t('nein_streifen_liegt_auf_der') },
  { value: 'groove', label: t('nut_fraesen_nicht_durchgehend') },
  { value: 'through', label: t('durchbruch_laser_stichsaege_mit_haltestegen') },
])
</script>

<template>
  <SettingsSection :title="t('n5_rahmen_ausschnitte')">
    <OptionGroup>
      <CheckboxField v-model="settings.frame" :label="t('viereckiger_led_rahmen')" />
      <FieldGrid v-if="settings.frame">
        <NumberField v-model="settings.frameInsetMm" :label="t('abstand_zum_rand_mm')" :min="0" :placeholder="`${t('auto')} (${(settings.marginCm * 5).toFixed(0)})`" />
        <SelectField v-model="settings.frameCorners" :label="t('ecken')" :options="corners" />
      </FieldGrid>
    </OptionGroup>

    <OptionGroup>
      <SelectField v-model="settings.cutMode" :label="t('led_im_brett_versenken')" :options="cutModes" />
      <FieldGrid v-if="settings.cutMode !== 'none'">
        <NumberField v-model="settings.cutTolerance" :label="t('spiel_zur_streifenbreite_mm')" :min="0" :step="0.1" />
        <NumberField v-if="settings.cutMode === 'groove'" v-model="settings.cutDepth" :label="t('nuttiefe_mm')" :min="1" :step="0.5" :placeholder="`${t('auto')} (${settings.stripWidth})`" />
        <NumberField v-else v-model="settings.bridgeWidth" :label="t('stegbreite_mm')" :min="2" />
      </FieldGrid>
      <HintText v-if="settings.cutMode === 'through'">{{ t('teile_die_komplett_von_ausschnitten') }}</HintText>
    </OptionGroup>
  </SettingsSection>
</template>
