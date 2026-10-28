// View state of the preview: which side, zoom, colours, highlighted piece (singleton).
import { reactive } from 'vue'

export const VIEWS = { FRONT: 'front', BACK: 'back', RESULT: 'result', CUT: 'cut' }

const state = reactive({
  view: VIEWS.FRONT,
  zoom: 1,
  showDims: true,
  neonColor: '#ff3cac',
  wallColor: '#0b0b0f',
  hover: null,
})

export function usePreviewState() {
  return state
}
