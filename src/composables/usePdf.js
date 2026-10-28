// Creates the printable PDF in the worker and hands it to the browser as a download.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { makePdf } from '@/util/engine'
import { usePlanner } from './usePlanner'
import { useSettings } from './useSettings'
import { useShare } from './useShare'

const busy = ref(false)

export function usePdf() {
  const { t, locale } = useI18n()
  const { plan, error } = usePlanner()
  const { settings } = useSettings()
  const { fileName } = useShare()

  async function download() {
    if (!plan.value) return
    busy.value = true
    try {
      const bytes = await makePdf(plan.value, { paper: settings.paper, parts: settings.parts, lang: locale.value })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }))
      link.download = `${fileName()}-${settings.paper}.pdf`
      link.click()
      setTimeout(() => URL.revokeObjectURL(link.href), 5000)
    } catch (e) {
      error.value = t('pdf_fehler') + (e.message || e)
    } finally {
      busy.value = false
    }
  }

  return { busy, download }
}
