<script setup>
import { useI18n } from 'vue-i18n'
import DangerButton from '@/components/button/DangerButton.vue'
import IconButton from '@/components/button/IconButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import AppIcon from '@/components/display/AppIcon.vue'
import { useEditor } from '@/composables/useEditor'

const { t } = useI18n()
const editor = useEditor()
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-zinc-800 bg-pink-950/30 px-3 py-1.5 text-xs text-pink-200">
    <span class="inline-flex gap-1">
      <IconButton :label="t('rueckgaengig')" :disabled="!editor.canUndo.value" @click="editor.undo"><AppIcon name="undo" :size="14" /></IconButton>
      <IconButton :label="t('wiederholen')" :disabled="!editor.canRedo.value" @click="editor.redo"><AppIcon name="redo" :size="14" /></IconButton>
    </span>
    <span>{{ t('editor_hint') }}</span>
    <DangerButton compact :disabled="editor.selected.value === null" @click="editor.deleteSelected">{{ t('stueck_loeschen') }}</DangerButton>
    <SecondaryButton compact @click="editor.discard">{{ t('alle_aenderungen_verwerfen') }}</SecondaryButton>
  </div>
</template>
