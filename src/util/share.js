// Save / load of a layout: JSON file and a compact share code (deflate + base64url).

async function deflate(text) {
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream('deflate-raw'))
  return new Uint8Array(await new Response(stream).arrayBuffer())
}
async function inflate(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'))
  return await new Response(stream).text()
}
const toB64url = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
function fromB64url(s) {
  const b = atob(s.replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(b, (c) => c.charCodeAt(0))
}

export const FORMAT = 'led-neon-planer'
export const VERSION = 1

export async function encodeCode(data) {
  const bytes = await deflate(JSON.stringify(data))
  let bin = ''
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return 'NP1.' + btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function decodeCode(code) {
  const s = code.trim().replace(/^.*#p=/, '')
  if (!s.startsWith('NP1.')) throw new Error('Unbekanntes Code-Format')
  return JSON.parse(await inflate(fromB64url(s.slice(4))))
}

export function downloadJson(data, name) {
  const blob = new Blob([JSON.stringify(data, null, 1)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 5000)
}

export { toB64url }
