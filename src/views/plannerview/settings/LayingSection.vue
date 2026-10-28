<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import HintText from '@/components/display/HintText.vue'
import CheckboxField from '@/components/input/CheckboxField.vue'
import FieldLabel from '@/components/input/FieldLabel.vue'
import NumberField from '@/components/input/NumberField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import SelectField from '@/components/input/SelectField.vue'
import FieldGrid from '@/components/layout/FieldGrid.vue'
import OptionGroup from '@/components/layout/OptionGroup.vue'
import SettingsSection from '@/components/layout/SettingsSection.vue'
import { useFonts } from '@/composables/useFonts'
import { useSettings } from '@/composables/useSettings'

const { t } = useI18n()
const { settings } = useSettings()
const { fontKind } = useFonts()

const modes = computed(() => [
  { value: 'contour', label: t('kontur_doppelt') },
  { value: 'single', label: t('form_einfach') },
])
const dotModes = computed(() => [
  { value: 'through', label: t('eigenes_stueck_uebergang_hinter_der') },
  { value: 'separate', label: t('eigenes_stueck_mit_eigenem_kabel') },
  { value: 'omit', label: t('ohne_led_z_b_aufgeklebt') },
])
const umlautStyles = computed(() => [
  { value: 'dots', label: t('n2_punkte') },
  { value: 'bar', label: t('waagerechter_strich') },
])
</script>

<template>
  <SettingsSection :title="t('n2_verlegung')">
    <SegmentedControl v-model="settings.mode" :options="modes" />
    <HintText>{{ settings.mode === 'contour' ? t('der_streifen_laeuft_innen_an') : t('der_streifen_folgt_dem_strich') }}</HintText>

    <FieldGrid v-if="settings.mode === 'contour'">
      <NumberField v-model="settings.contourOffset" :label="t('abstand_zum_rand_mm')" :step="0.5" :placeholder="`${t('auto')} (${settings.stripWidth / 2})`" />
      <NumberField v-if="fontKind === 'hershey'" v-model="settings.hersheyStroke" :label="t('strichbreite_mm')" :placeholder="`${t('auto')} (${settings.stripWidth * 3})`" />
    </FieldGrid>

    <OptionGroup>
      <CheckboxField v-model="settings.autoSmooth" :label="t('zu_enge_stellen_automatisch_glaetten')" />
      <HintText>{{ t('ohne_diese_option_folgt_der') }}</HintText>
      <FieldGrid v-if="settings.autoSmooth">
        <NumberField v-model="settings.smoothRadiusCm" :label="t('glaetten_bis_radius_cm')" :min="0" :step="0.1" :placeholder="`${t('biegeradius')} (${settings.bendRadiusCm})`" />
        <NumberField v-model="settings.smoothMaxDev" :label="t('dabei_max_abweichung_mm')" :min="0" />
      </FieldGrid>
    </OptionGroup>

    <SelectField v-model="settings.dotMode" :label="t('punkte_i_j_ae_oe')" :options="dotModes" />
    <div>
      <FieldLabel>{{ t('umlaute_ae_oe_ue') }}</FieldLabel>
      <SegmentedControl v-model="settings.umlautStyle" :options="umlautStyles" />
    </div>
  </SettingsSection>
</template>
