<script setup>
import { onMounted } from 'vue'
import { useEditor } from '@/composables/useEditor'
import { useFonts } from '@/composables/useFonts'
import { usePlanner } from '@/composables/usePlanner'
import { useShare } from '@/composables/useShare'
import { useKeyboard } from '@/composables/useKeyboard'
import LoadingCard from './plannerview/LoadingCard.vue'
import PreviewPanel from './plannerview/preview/PreviewPanel.vue'
import CutListTable from './plannerview/results/CutListTable.vue'
import CutOutInfo from './plannerview/results/CutOutInfo.vue'
import HiddenTransitions from './plannerview/results/HiddenTransitions.vue'
import LayingOrderTable from './plannerview/results/LayingOrderTable.vue'
import PlanMessages from './plannerview/results/PlanMessages.vue'
import SummaryCards from './plannerview/results/SummaryCards.vue'
import SettingsSidebar from './plannerview/SettingsSidebar.vue'

/** The single page of the app: settings on the left, preview and results on the right. */
const { plan, start } = usePlanner()
const { loadCatalogue } = useFonts()
const share = useShare()
const editor = useEditor()

useKeyboard({
  'mod+z': editor.undo,
  'mod+shift+z': editor.redo,
  'mod+y': editor.redo,
  delete: editor.deleteSelected,
  backspace: editor.deleteSelected,
  enter: () => editor.draft.value && editor.finishDrawing(false),
  escape: () => {
    if (editor.draft.value) return editor.cancelDrawing()
    editor.selected.value = null
    editor.closeMenu()
  },
}, () => editor.active.value)

onMounted(async () => {
  await loadCatalogue()
  if (location.hash.startsWith('#p=')) await share.loadCode(location.hash, true)
  await start()
})
</script>

<template>
  <div class="min-h-screen lg:flex">
    <SettingsSidebar />
    <main class="min-w-0 flex-1 space-y-4 p-4 lg:h-screen lg:overflow-y-auto">
      <LoadingCard v-if="!plan" />
      <template v-else>
        <PreviewPanel />
        <PlanMessages />
        <SummaryCards />
        <HiddenTransitions />
        <CutOutInfo />
        <div class="grid gap-4 xl:grid-cols-2">
          <CutListTable />
          <LayingOrderTable />
        </div>
      </template>
    </main>
  </div>
</template>
