<script setup>
// Font dropdown that renders every entry in its own typeface (Hershey fonts as SVG strokes).
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { hersheyPath, parseHershey } from '@/util/hershey.js'

const { t } = useI18n()
const CATEGORY_KEYS = {
  'Schreibschrift': 'schreibschrift', 'Schreibschrift (dünn)': 'schreibschrift_duenn', 'Serifenlos': 'serifenlos',
  'Gerundet': 'gerundet', 'Einlinien (Hershey)': 'einlinien_hershey', 'Eigene Schrift': 'eigene_schrift',
}
const catLabel = (c) => (CATEGORY_KEYS[c] ? t(CATEGORY_KEYS[c]) : c)

const props = defineProps({
  fonts: Array,           // catalogue entries from fonts.json
  modelValue: String,     // selected font id
  custom: Object,         // uploaded font { id: 'custom', name, kind }
  sample: String,
  base: String,
  weight: Number,         // weight used for variable fonts in the preview
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const root = ref(null)
const hershey = ref({})        // id -> parsed glyphs
const loaded = ref(new Set())  // outline font ids registered as FontFace

const sampleText = computed(() => (props.sample || '').split('\n')[0].trim().slice(0, 24) || 'Hallo')
const all = computed(() => [...props.fonts, ...(props.custom ? [props.custom] : [])])
const current = computed(() => all.value.find((f) => f.id === props.modelValue))
const groups = computed(() => {
  const g = {}
  for (const f of all.value) (g[f.category || 'Eigene Schrift'] ||= []).push(f)
  return g
})

async function ensure(font) {
  if (!font || font.id === 'custom') return
  if (font.kind === 'hershey') {
    if (hershey.value[font.id]) return
    const txt = await (await fetch(`${props.base}fonts/${font.file}`)).text()
    hershey.value = { ...hershey.value, [font.id]: parseHershey(txt) }
  } else if (!loaded.value.has(font.id)) {
    const face = new FontFace(`np-${font.id}`, `url(${props.base}fonts/${font.file})`)
    try {
      document.fonts.add(await face.load())
      loaded.value = new Set([...loaded.value, font.id])
    } catch { /* preview falls back to system font */ }
  }
}

watch(open, (o) => { if (o) props.fonts.forEach(ensure) })
watch(current, ensure, { immediate: true })

function preview(font) {
  const glyphs = hershey.value[font.id]
  if (!glyphs) return null
  const { d, width } = hersheyPath(glyphs, sampleText.value)
  return { d, viewBox: `-2 -14 ${width + 4} 26` }
}

function pick(id) {
  emit('update:modelValue', id)
  open.value = false
}
function onDoc(e) { if (root.value && !root.value.contains(e.target)) open.value = false }
onMounted(() => document.addEventListener('mousedown', onDoc))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDoc))
</script>

<template>
  <div ref="root" class="relative">
    <button type="button" class="flex w-full items-center justify-between gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-left text-sm text-zinc-100 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/60 focus:outline-none" @click="open = !open">
      <span class="min-w-0 flex-1">
        <span class="block text-[11px] text-zinc-500">{{ current?.name || t('schrift_waehlen') }}</span>
        <span v-if="current && current.kind === 'hershey' && preview(current)" class="block h-7">
          <svg :viewBox="preview(current).viewBox" class="h-full max-w-full" preserveAspectRatio="xMinYMid meet">
            <path :d="preview(current).d" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </span>
        <span v-else class="block truncate text-xl leading-7" :style="{ fontFamily: `np-${current?.id}, sans-serif`, fontVariationSettings: current?.weight && weight ? `'wght' ${weight}` : null }">{{ sampleText }}</span>
      </span>
      <svg class="h-4 w-4 shrink-0 text-zinc-500" viewBox="0 0 20 20" fill="currentColor"><path d="M5.5 7.5 10 12l4.5-4.5" stroke="currentColor" stroke-width="1.5" fill="none" /></svg>
    </button>

    <div v-if="open" class="absolute z-30 mt-1 max-h-[60vh] w-full overflow-y-auto rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl shadow-black/60">
      <template v-for="(list, cat) in groups" :key="cat">
        <div class="sticky top-0 bg-zinc-900/95 px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 backdrop-blur">{{ catLabel(cat) }}</div>
        <button
          v-for="f in list" :key="f.id" type="button"
          class="block w-full px-3 py-1.5 text-left hover:bg-pink-500/10"
          :class="f.id === modelValue ? 'bg-pink-500/15 text-pink-200' : 'text-zinc-100'"
          @click="pick(f.id)"
        >
          <span class="block text-[11px] text-zinc-500">{{ f.name }}</span>
          <span v-if="f.kind === 'hershey'" class="block h-8">
            <svg v-if="preview(f)" :viewBox="preview(f).viewBox" class="h-full max-w-full" preserveAspectRatio="xMinYMid meet">
              <path :d="preview(f).d" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span v-else class="block truncate text-2xl leading-8" :style="{ fontFamily: `np-${f.id}, sans-serif`, fontVariationSettings: f.weight && weight ? `'wght' ${weight}` : null }">{{ sampleText }}</span>
        </button>
      </template>
    </div>
  </div>
</template>
