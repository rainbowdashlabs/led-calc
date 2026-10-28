// Runs the Python core in the worker: initialises it, recomputes the plan whenever the
// parameters change (debounced) and reports progress (singleton).
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { compute, initEngine } from '@/util/engine'
import { useFonts } from './useFonts'
import { useManualEdits } from './useManualEdits'
import { useNotice } from './useNotice'
import { useSettings } from './useSettings'

const plan = ref(null)
const error = ref('')
const ready = ref(false)
const progress = reactive({ active: true, fraction: 0, label: 'lade_python_umgebung' })
let started = false

const DEBOUNCE_MS = 350

export function usePlanner() {
  const { locale, t } = useI18n()
  const { settings, params, geometrySignature } = useSettings()
  const { fontKind, effectiveWeight, weightInfo, fontBytes } = useFonts()
  const manual = useManualEdits()
  const { flash } = useNotice()

  const currentParams = computed(() => params({
    lang: locale.value,
    fontKind: fontKind.value,
    weight: weightInfo.value ? effectiveWeight.value : null,
  }))
  const signature = computed(() => geometrySignature(currentParams.value))

  let timer = null
  let runId = 0

  function schedule() {
    clearTimeout(timer)
    timer = setTimeout(run, DEBOUNCE_MS)
  }

  async function run() {
    if (!ready.value) return
    const id = ++runId
    const bytes = await fontBytes()
    if (!bytes || !settings.text.trim()) return
    const edits = manual.validFor(signature.value)
    if (edits.stale) flash(t('manuelle_aenderungen_wurden_verworfen_weil'))
    Object.assign(progress, { active: true, fraction: 0, label: 'Berechnung' })
    try {
      const res = await compute(currentParams.value, bytes, edits.pieces, (p) => {
        if (id === runId) Object.assign(progress, p)
      })
      if (id !== runId) return
      if (res.ok) {
        plan.value = res
        error.value = ''
      } else {
        error.value = res.warnings.join(' ')
      }
    } catch (e) {
      if (id === runId) error.value = String(e.message || e)
    } finally {
      if (id === runId) progress.active = false
    }
  }

  /** Load Python once; afterwards every parameter change triggers a recomputation. */
  async function start() {
    if (started) return
    started = true
    try {
      await initEngine((p) => Object.assign(progress, { fraction: p.fraction * 0.95, label: p.label }))
      ready.value = true
      watch(() => [JSON.stringify(currentParams.value), settings.fontId], schedule)
      run()
    } catch (e) {
      progress.label = t('fehler_beim_laden') + (e.message || e)
    }
  }

  return { plan, error, progress, ready, currentParams, signature, start, schedule }
}
