<script setup>
import { onMounted } from 'vue'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useEditor } from '@/composables/useEditor'
import { useFonts } from '@/composables/useFonts'
import { useKeyboard } from '@/composables/useKeyboard'
import { useMobileTabs } from '@/composables/useMobileTabs'
import { usePlanner } from '@/composables/usePlanner'
import { useShare } from '@/composables/useShare'
import LoadingCard from './plannerview/LoadingCard.vue'
import MobileHeader from './plannerview/MobileHeader.vue'
import MobileTabBar from './plannerview/MobileTabBar.vue'
import PreviewPanel from './plannerview/preview/PreviewPanel.vue'
import ResultsPanel from './plannerview/results/ResultsPanel.vue'
import SummaryCards from './plannerview/results/SummaryCards.vue'
import SettingsSidebar from './plannerview/SettingsSidebar.vue'

/**
 * The single page of the app. On desktops settings, preview and results are side by side;
 * on phones and tablets a tab bar switches between them.
 */
const { plan, start } = usePlanner()
const { loadCatalogue } = useFonts()
const share = useShare()
const editor = useEditor()
const { isDesktop } = useBreakpoint()
const { tab, TABS } = useMobileTabs()

const shows = (area) => isDesktop.value || tab.value === area

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
  <div class="min-h-dvh pb-[calc(4rem+env(safe-area-inset-bottom))] lg:flex lg:pb-0">
    <div class="lg:hidden print:hidden"><MobileHeader /></div>
    <div v-show="shows(TABS.SETTINGS)" class="print:hidden">
      <SettingsSidebar />
    </div>
    <main class="min-w-0 flex-1 lg:h-dvh lg:overflow-y-auto">
      <div class="mx-auto max-w-[110rem] space-y-4 p-3 sm:p-4 2xl:p-6">
        <LoadingCard v-if="!plan" v-show="shows(TABS.PREVIEW) || shows(TABS.RESULTS)" />
        <template v-else>
          <div v-show="shows(TABS.PREVIEW)" class="space-y-4">
            <PreviewPanel />
            <!-- small screens: the key figures right below the preview -->
            <div v-if="!isDesktop"><SummaryCards /></div>
          </div>
          <div v-show="shows(TABS.RESULTS)"><ResultsPanel /></div>
        </template>
      </div>
    </main>
    <div class="lg:hidden print:hidden"><MobileTabBar /></div>
  </div>
</template>
