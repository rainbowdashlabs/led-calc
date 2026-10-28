// Minimal Hershey (.jhf) parser for rendering font previews in the picker.
export function parseHershey(text) {
  const glyphs = {}
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  lines.forEach((line, idx) => {
    const body = line.slice(8)
    const R = 'R'.charCodeAt(0)
    const left = body.charCodeAt(0) - R
    const right = body.charCodeAt(1) - R
    const strokes = []
    let cur = []
    for (let i = 2; i + 1 < body.length; i += 2) {
      const pair = body.slice(i, i + 2)
      if (pair === ' R') {
        if (cur.length > 1) strokes.push(cur)
        cur = []
        continue
      }
      cur.push([body.charCodeAt(i) - R - left, body.charCodeAt(i + 1) - R])
    }
    if (cur.length > 1) strokes.push(cur)
    glyphs[String.fromCharCode(32 + idx)] = { width: right - left, strokes }
  })
  return glyphs
}

const FALLBACK = { ä: 'a', ö: 'o', ü: 'u', Ä: 'A', Ö: 'O', Ü: 'U', ß: 's' }

// SVG path data for a text sample; returns { d, width } in Hershey units (y down, baseline 9).
export function hersheyPath(glyphs, text) {
  let x = 0
  const parts = []
  for (const ch of text) {
    const g = glyphs[ch] || glyphs[FALLBACK[ch]] || glyphs['?']
    if (!g) continue
    for (const s of g.strokes) parts.push('M' + s.map(([px, py]) => `${(px + x).toFixed(1)},${py}`).join('L'))
    x += g.width
  }
  return { d: parts.join(''), width: Math.max(x, 1) }
}
