<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AccentButton from '@/components/button/AccentButton.vue'
import PrimaryButton from '@/components/button/PrimaryButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import CheckboxField from '@/components/input/CheckboxField.vue'
import ColorField from '@/components/input/ColorField.vue'
import SegmentedControl from '@/components/input/SegmentedControl.vue'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useEditor } from '@/composables/useEditor'
import { usePreviewState, VIEWS } from '@/composables/usePreviewState'
import { useSettings } from '@/composables/useSettings'
import ZoomControl from './ZoomControl.vue'

defineEmits(['fit'])
const { t } = useI18n()
const preview = usePreviewState()
const editor = useEditor()
const { settings } = useSettings()
const { isNarrow } = useBreakpoint()

const views = computed(() => [
  { value: VIEWS.FRONT, label: t(isNarrow.value ? 'kurz_vorne' : 'vorderseite') },
  { value: VIEWS.BACK, label: t(isNarrow.value ? 'kurz_hinten' : 'rueckseite_gespiegelt'), disabled: editor.active.value },
  { value: VIEWS.RESULT, label: t('ergebnis'), disabled: editor.active.value },
  ...(settings.cutMode !== 'none' ? [{ value: VIEWS.CUT, label: t(isNarrow.value ? 'kurz_ausschnitte' : 'ausschnitte'), disabled: editor.active.value }] : []),
])
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 px-2 py-2 sm:px-3 print:hidden">
    <SegmentedControl v-model="preview.view" :options="views" class="w-full sm:w-auto" />
    <div class="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
      <ColorField v-if="preview.view === VIEWS.RESULT" v-model="preview.wallColor" :label="t('wand')" inline />
      <CheckboxField v-model="preview.showDims" :label="t('masse')" class="!text-xs !text-zinc-400" />
      <ZoomControl v-model="preview.zoom" />
      <SecondaryButton compact :title="t('ganze_platte_anzeigen')" @click="$emit('fit')">{{ t('einpassen') }}</SecondaryButton>
      <AccentButton v-if="!editor.active.value" compact @click="editor.start">{{ t('pfade_bearbeiten') }}</AccentButton>
      <PrimaryButton v-else compact @click="editor.finish">{{ t('bearbeitung_beenden') }}</PrimaryButton>
    </div>
  </div>
</template>
