// Which area is shown on small screens (settings, preview or results) (singleton).
import { ref } from 'vue'

export const TABS = { SETTINGS: 'settings', PREVIEW: 'preview', RESULTS: 'results' }

const tab = ref(TABS.PREVIEW)

export function useMobileTabs() {
  return { tab, TABS }
}
