// File exports of the current plan, created in the worker: the printable PDF templates
// and a DXF file for CNC milling.
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { saveFile } from '@/util/download'
import { makeDxf, makePdf } from '@/util/engine'
import { usePlanner } from './usePlanner'
import { useSettings } from './useSettings'
import { useShare } from './useShare'

const busy = reactive({ pdf: false, dxf: false })

export function useExport() {
  const { t, locale } = useI18n()
  const { plan, error } = usePlanner()
  const { settings } = useSettings()
  const { fileName } = useShare()

  /** Run one export, keeping its busy flag and reporting failures. */
  async function run(kind, create) {
    if (!plan.value || busy[kind]) return
    busy[kind] = true
    try {
      await create()
    } catch (e) {
      error.value = t('export_fehler', { kind: kind.toUpperCase() }) + (e.message || e)
    } finally {
      busy[kind] = false
    }
  }

  const downloadPdf = () => run('pdf', async () => {
    const bytes = await makePdf(plan.value, { paper: settings.paper, parts: settings.parts, lang: locale.value })
    saveFile(bytes, 'application/pdf', `${fileName()}-${settings.paper}.pdf`)
  })

  const downloadDxf = () => run('dxf', async () => {
    const text = await makeDxf(plan.value)
    saveFile(text, 'application/dxf', `${fileName()}-cnc.dxf`)
  })

  return { busy, downloadPdf, downloadDxf }
}
