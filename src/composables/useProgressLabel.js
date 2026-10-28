// The worker and Python report progress steps in German; this maps them to message keys.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlanner } from './usePlanner'

const LABEL_KEYS = {
  'Python wird geladen': 'python_wird_geladen',
  'Geometrie-Bibliotheken werden geladen': 'geometrie_bibliotheken_werden_geladen',
  bereit: 'bereit',
  Berechnung: 'berechnung',
  'Schrift setzen': 'schrift_setzen',
  'Formen analysieren': 'formen_analysieren',
  'Streifenbahnen erzeugen': 'streifenbahnen_erzeugen',
  'Biegeradien optimieren': 'biegeradien_optimieren',
  'Haltestege planen': 'haltestege_planen',
  'Routing hinter der Platte': 'routing_hinter_der_platte',
  'Ausschnitte berechnen': 'ausschnitte_berechnen',
  fertig: 'fertig',
}

export function useProgressLabel() {
  const { t } = useI18n()
  const { progress } = usePlanner()
  return computed(() => t(LABEL_KEYS[progress.label] ?? progress.label))
}
