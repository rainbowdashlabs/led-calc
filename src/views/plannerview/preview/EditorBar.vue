<script setup>
import { useI18n } from 'vue-i18n'
import AccentButton from '@/components/button/AccentButton.vue'
import DangerButton from '@/components/button/DangerButton.vue'
import IconButton from '@/components/button/IconButton.vue'
import PrimaryButton from '@/components/button/PrimaryButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import AppIcon from '@/components/display/AppIcon.vue'
import { useEditor } from '@/composables/useEditor'

const { t } = useI18n()
const editor = useEditor()
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-zinc-800 bg-pink-950/30 px-3 py-1.5 text-xs text-pink-200">
    <template v-if="editor.draft.value">
      <span>{{ t('zeichnen_hint') }}</span>
      <PrimaryButton compact :disabled="editor.draft.value.length < 2" @click="editor.finishDrawing(false)">{{ t('fertig') }}</PrimaryButton>
      <SecondaryButton compact @click="editor.cancelDrawing">{{ t('abbrechen') }}</SecondaryButton>
    </template>
    <template v-else>
      <span class="inline-flex gap-1">
        <IconButton :label="t('rueckgaengig')" :disabled="!editor.canUndo.value" @click="editor.undo"><AppIcon name="undo" :size="14" /></IconButton>
        <IconButton :label="t('wiederholen')" :disabled="!editor.canRedo.value" @click="editor.redo"><AppIcon name="redo" :size="14" /></IconButton>
      </span>
      <AccentButton compact @click="editor.startDrawing"><AppIcon name="plus" :size="14" />{{ t('neues_stueck') }}</AccentButton>
      <span>{{ t('editor_hint') }}</span>
      <DangerButton compact :disabled="editor.selected.value === null" @click="editor.deleteSelected">{{ t('stueck_loeschen') }}</DangerButton>
      <SecondaryButton compact @click="editor.discard">{{ t('alle_aenderungen_verwerfen') }}</SecondaryButton>
    </template>
  </div>
</template>
