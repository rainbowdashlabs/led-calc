// Number formatting that follows the UI language.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export function useFormat() {
  const { locale } = useI18n()
  const tag = computed(() => (locale.value === 'de' ? 'de-DE' : 'en-GB'))
  const fmtLen = (mm) => (mm >= 1000
    ? `${(mm / 1000).toLocaleString(tag.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`
    : `${Math.round(mm / 10).toLocaleString(tag.value)} cm`)
  const fmtMm = (mm) => `${Math.round(mm).toLocaleString(tag.value)} mm`
  const fmtCm = (mm) => `${(mm / 10).toLocaleString(tag.value, { maximumFractionDigits: 1 })} cm`
  return { fmtLen, fmtMm, fmtCm }
}
