// Web worker that hosts Pyodide and the `neonplan` Python package.
// Keeps the UI responsive while geometry and PDF generation run.
const PYODIDE_VERSION = '314.0.7'
 
const PYODIDE_URL = __LOCAL_PYODIDE__
  ? new URL('../pyodide/', self.location.href).href // resolved at runtime (not rewritten by Vite)
  : `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

// Python sources are bundled as raw strings at build time.
const sources = import.meta.glob('../python/neonplan/*.py', { query: '?raw', import: 'default', eager: true })

let pyodide = null
let ready = null

async function init(report) {
  report(0.05, 'Python wird geladen')
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL })
  report(0.5, 'Geometrie-Bibliotheken werden geladen')
  await pyodide.loadPackage(['numpy', 'shapely', 'fonttools'])
  pyodide.FS.mkdirTree('/home/pyodide/neonplan')
  for (const [path, code] of Object.entries(sources)) {
    pyodide.FS.writeFile(`/home/pyodide/neonplan/${path.split('/').pop()}`, code)
  }
  await pyodide.runPythonAsync(`
import sys, json
sys.path.insert(0, '/home/pyodide')
from neonplan import api
`)
  report(1, 'bereit')
}

self.onmessage = async (ev) => {
  const { id, type, payload } = ev.data
  const report = (fraction, label) => self.postMessage({ id, progress: { fraction, label } })
  try {
    if (!ready) ready = init(report)
    await ready
    if (type === 'init') {
      self.postMessage({ id, ok: true })
    } else if (type === 'compute') {
      pyodide.globals.set('font_bytes', payload.font)
      pyodide.globals.set('params_json', JSON.stringify(payload.params))
      pyodide.globals.set('manual_json', JSON.stringify(payload.manual ?? null))
      pyodide.globals.set('js_progress', report)
      const out = await pyodide.runPythonAsync(
        `json.dumps(api.compute(json.loads(params_json), bytes(font_bytes.to_py()), progress=js_progress, manual=json.loads(manual_json)))`,
      )
      self.postMessage({ id, ok: true, result: JSON.parse(out) })
    } else if (type === 'dxf') {
      pyodide.globals.set('plan_json', JSON.stringify(payload.plan))
      const text = await pyodide.runPythonAsync('api.make_dxf(json.loads(plan_json))')
      self.postMessage({ id, ok: true, result: text })
    } else if (type === 'pdf') {
      pyodide.globals.set('plan_json', JSON.stringify(payload.plan))
      pyodide.globals.set('pdf_opts', JSON.stringify(payload.options))
      const proxy = await pyodide.runPythonAsync(`
_o = json.loads(pdf_opts)
api.make_pdf(json.loads(plan_json), paper=_o['paper'], parts=tuple(_o['parts']), lang=_o.get('lang'))
`)
      const bytes = proxy.toJs()
      proxy.destroy?.()
      self.postMessage({ id, ok: true, result: bytes }, [bytes.buffer])
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err?.message || err) })
  }
}
