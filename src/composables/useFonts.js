// Font catalogue, the selected font, its bytes and the weight of variable fonts (singleton).
import { computed, ref, watch } from 'vue'
import { useSettings } from './useSettings'

const fonts = ref([])
const customFont = ref(null) // { id: 'custom', name, bytes, kind, category }
const cache = new Map()
const base = import.meta.env.BASE_URL

export function useFonts() {
  const { settings } = useSettings()
  const selectedFont = computed(() => (settings.fontId === 'custom' ? customFont.value : fonts.value.find((x) => x.id === settings.fontId)))
  const fontKind = computed(() => selectedFont.value?.kind || 'outline')
  const weightInfo = computed(() => selectedFont.value?.weight || null)
  // weight actually used: explicit, else thin for single-line and bold for outlines
  const autoWeight = computed(() => (weightInfo.value ? weightInfo.value[settings.mode === 'single' ? 'single' : 'contour'] : null))
  const effectiveWeight = computed(() => (weightInfo.value ? (settings.fontWeight ?? autoWeight.value) : null))

  async function loadCatalogue() {
    fonts.value = await (await fetch(`${base}fonts/fonts.json`)).json()
    if (settings.fontId === 'custom' || !fonts.value.some((x) => x.id === settings.fontId)) settings.fontId = 'pacifico'
  }

  async function fontBytes() {
    const font = selectedFont.value
    if (!font) return null
    if (font.bytes) return font.bytes
    if (!cache.has(font.id)) {
      const res = await fetch(`${base}fonts/${font.file}`)
      cache.set(font.id, new Uint8Array(await res.arrayBuffer()))
    }
    return cache.get(font.id)
  }

  function setCustomFont(name, bytes) {
    const kind = name.toLowerCase().endsWith('.jhf') ? 'hershey' : 'outline'
    customFont.value = { id: 'custom', name, bytes, kind, category: 'Eigene Schrift' }
    if (kind === 'outline') new FontFace('np-custom', bytes).load().then((ff) => document.fonts.add(ff)).catch(() => {})
  }

  return { base, fonts, customFont, selectedFont, fontKind, weightInfo, effectiveWeight, loadCatalogue, fontBytes, setCustomFont }
}

// a new font starts with the automatic weight again
watch(() => useSettings().settings.fontId, () => { useSettings().settings.fontWeight = null })
