// Promise wrapper around the Pyodide worker with progress callbacks.
const worker = new Worker(new URL('../worker.js', import.meta.url), { type: 'module' })
let seq = 0
const pending = new Map()

worker.onmessage = (ev) => {
  const { id, ok, result, error, progress } = ev.data
  const p = pending.get(id)
  if (!p) return
  if (progress) {
    p.onProgress?.(progress)
    return
  }
  pending.delete(id)
  ok ? p.resolve(result) : p.reject(new Error(error))
}

function call(type, payload, onProgress) {
  const id = ++seq
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject, onProgress })
    worker.postMessage({ id, type, payload })
  })
}

export const initEngine = (onProgress) => call('init', null, onProgress)
// Vue reactive proxies cannot be cloned into a worker: send plain data
const plain = (x) => (x == null ? x : JSON.parse(JSON.stringify(x)))
export const compute = (params, font, manual, onProgress) => call('compute', { params, font, manual: plain(manual) }, onProgress)
export const makePdf = (plan, options) => call('pdf', { plan: plain(plan), options: plain(options) })
export const makeDxf = (plan) => call('dxf', { plan: plain(plan) })
