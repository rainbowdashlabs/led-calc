// Geometry for the path editor: a path is a list of handles (points on the path), a
// type per handle ('smooth' | 'corner') and a type per segment ('curve' | 'line').

const sub = (a, b) => [a[0] - b[0], a[1] - b[1]]
const len = (v) => Math.hypot(v[0], v[1])
const unit = (v) => { const l = len(v) || 1e-9; return [v[0] / l, v[1] / l] }
const dot = (a, b) => a[0] * b[0] + a[1] * b[1]
const r2 = ([x, y]) => [Math.round(x * 100) / 100, Math.round(y * 100) / 100]

/** Mirror tangent t about the chord direction c (natural end of a curve segment). */
function mirror(t, c) {
  const d = 2 * dot(c, t)
  return unit([d * c[0] - t[0], d * c[1] - t[1]])
}

/**
 * Build the path through the handles.
 * - line segments are straight;
 * - curve segments are cubic Beziers whose handle lengths reproduce circular arcs exactly;
 * - at a 'smooth' handle the curve continues tangentially (also into an adjacent line);
 * - at a 'corner' handle both sides are independent (a kink, rounded later with the
 *   minimum bend radius when the plan is computed).
 */
export function buildPath(h, types, segs, closed, step = 1.5) {
  const n = h.length
  if (n < 2) return h.map(r2)
  const segCount = closed ? n : n - 1
  const seg = (i) => (segs?.[i] ?? 'curve')
  const typ = (i) => (types?.[i] ?? 'smooth')
  const next = (i) => (i + 1) % n
  const chord = (i) => unit(sub(h[next(i)], h[i]))           // direction of segment i
  const prevSeg = (i) => (closed ? (i - 1 + n) % n : i - 1)   // segment ending at handle i

  // shared tangent at smooth handles
  const tan = h.map((_, i) => {
    if (typ(i) !== 'smooth') return null
    const a = prevSeg(i) >= 0 ? prevSeg(i) : null
    const b = i < segCount ? i : null
    if (a !== null && seg(a) === 'line' && !(b !== null && seg(b) === 'line')) return chord(a)
    if (b !== null && seg(b) === 'line' && !(a !== null && seg(a) === 'line')) return chord(b)
    if (a === null) return null // open start: natural end, handled per segment
    if (b === null) return null
    return unit(sub(h[next(i)], h[(i - 1 + n) % n]))
  })

  const out = []
  for (let i = 0; i < segCount; i++) {
    const p0 = h[i], p3 = h[next(i)]
    const c = len(sub(p3, p0))
    const m = Math.max(2, Math.ceil(c / step))
    if (seg(i) === 'line' || c < 1e-9) {
      for (let k = 0; k < m; k++) out.push([p0[0] + ((p3[0] - p0[0]) * k) / m, p0[1] + ((p3[1] - p0[1]) * k) / m])
      continue
    }
    const ch = chord(i)
    let t0 = tan[i]
    let t1 = tan[next(i)]
    if (!t0 && !t1) { t0 = ch; t1 = ch }
    else if (!t0) t0 = mirror(t1, ch)
    else if (!t1) t1 = mirror(t0, ch)
    const turn = Math.acos(Math.max(-1, Math.min(1, dot(t0, t1))))
    const hl = turn < 1e-6 ? c / 3 : ((4 / 3) * Math.tan(turn / 4) * c) / (2 * Math.sin(turn / 2))
    const p1 = [p0[0] + t0[0] * hl, p0[1] + t0[1] * hl]
    const p2 = [p3[0] - t1[0] * hl, p3[1] - t1[1] * hl]
    for (let k = 0; k < m; k++) {
      const t = k / m, u = 1 - t
      const b0 = u * u * u, b1 = 3 * u * u * t, b2 = 3 * u * t * t, b3 = t * t * t
      out.push([b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0], b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1]])
    }
  }
  if (!closed) out.push(h[n - 1])
  return out.map(r2)
}

/** Distance from point p to the polyline and index of the closest segment. */
export function nearestSegment(pts, closed, p) {
  let best = 0
  let bestD = Infinity
  const n = pts.length
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const a = pts[i], b = pts[(i + 1) % n]
    const dx = b[0] - a[0], dy = b[1] - a[1]
    const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy || 1)))
    const d = Math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])
    if (d < bestD) { bestD = d; best = i }
  }
  return { index: best, distance: bestD }
}

function maxDeviation(pts, i0, i1) {
  const a = pts[i0], b = pts[i1]
  const d = sub(b, a)
  const L = len(d) || 1e-9
  let m = 0
  for (let i = i0 + 1; i < i1; i++) {
    const v = sub(pts[i], a)
    m = Math.max(m, Math.abs(v[0] * d[1] - v[1] * d[0]) / L)
  }
  return m
}

/**
 * Editable representation of a path with as few handles as possible: starts with 4 points
 * on a ring (2 on an open path) and adds a handle where the curve deviates most, until it
 * stays within `tol`. Straight stretches become 'line' segments, kinks 'corner' handles.
 * An "o" needs about 4 handles, a "u" about 5-6.
 */
export function editableFrom(pts, closed, tol = 3.0, maxHandles = 60) {
  const n = pts.length
  if (n < 3) return { handles: pts.map(r2), types: pts.map(() => 'smooth'), segs: pts.slice(1).map(() => 'line') }
  const cum = [0]
  for (let i = 1; i < n; i++) cum.push(cum[i - 1] + len(sub(pts[i], pts[i - 1])))
  const total = cum[n - 1] + (closed ? len(sub(pts[0], pts[n - 1])) : 0)
  const atLength = (L) => { const i = cum.findIndex((c) => c >= L); return i < 0 ? n - 1 : i }
  let idx = closed ? [0, 1, 2, 3].map((k) => atLength((total * k) / 4)) : [0, n - 1]
  idx = [...new Set(idx)].sort((a, b) => a - b)
  const probe = []
  for (let i = 0; i < n; i += Math.max(1, Math.floor(n / 200))) probe.push(i)

  const classify = (ids) => {
    const m = ids.length
    const segCount = closed ? m : m - 1
    const segs = []
    for (let k = 0; k < segCount; k++) {
      const i0 = ids[k], i1 = k + 1 < m ? ids[k + 1] : n - 1
      const straight = i1 > i0 + 2 && maxDeviation(pts, i0, i1) < 0.6 && len(sub(pts[i1], pts[i0])) > 8
      segs.push(straight ? 'line' : 'curve')
    }
    const types = ids.map((_, k) => {
      const a = closed ? (k - 1 + m) % m : k - 1
      if (a < 0 || k >= segCount) return 'smooth'
      if (segs[a] === 'line' && segs[k] === 'line') {
        const d1 = unit(sub(pts[ids[k]], pts[ids[a]]))
        const d2 = unit(sub(pts[ids[(k + 1) % m]], pts[ids[k]]))
        return dot(d1, d2) < Math.cos((20 * Math.PI) / 180) ? 'corner' : 'smooth'
      }
      return 'smooth'
    })
    return { segs, types }
  }

  for (let iter = 0; iter < maxHandles; iter++) {
    const { segs, types } = classify(idx)
    const curve = buildPath(idx.map((i) => pts[i]), types, segs, closed, 2)
    let worst = -1
    let worstD = tol
    for (const i of probe) {
      const d = nearestSegment(curve, closed, pts[i]).distance
      if (d > worstD) { worstD = d; worst = i }
    }
    if (worst < 0 || idx.includes(worst)) break
    idx = [...idx, worst].sort((a, b) => a - b)
  }
  const { segs, types } = classify(idx)
  return { handles: idx.map((i) => r2(pts[i])), types, segs }
}

/** Point presets for the point menu: [handle type, incoming segment, outgoing segment]. */
export const POINT_PRESETS = {
  round: ['smooth', 'curve', 'curve'],
  corner: ['corner', 'line', 'line'],
  line_curve_tangent: ['smooth', 'line', 'curve'],
  curve_line_tangent: ['smooth', 'curve', 'line'],
  line_curve_corner: ['corner', 'line', 'curve'],
  curve_line_corner: ['corner', 'curve', 'line'],
  curve_curve_corner: ['corner', 'curve', 'curve'],
}

/** Which preset matches a handle (for highlighting in the menu). */
export function presetOf(e, i) {
  const n = e.handles.length
  const segCount = e.closed ? n : n - 1
  const a = e.closed ? (i - 1 + n) % n : i - 1
  const inn = a >= 0 ? e.segs[a] : null
  const out = i < segCount ? e.segs[i] : null
  for (const [k, [t, si, so]] of Object.entries(POINT_PRESETS)) {
    if (t === e.types[i] && (inn === null || inn === si) && (out === null || out === so)) return k
  }
  return null
}

/** Same piece with its direction reversed (handles, point and segment types). */
export function reversed(piece) {
  return {
    ...piece,
    handles: [...piece.handles].reverse(),
    types: [...piece.types].reverse(),
    segs: [...piece.segs].reverse(),
  }
}

/**
 * Join two open pieces end to end. `endA` / `endB` are 'start' | 'end'; the two ends meet
 * in one smooth point. Joining both ends of the same piece closes it into a ring.
 * Returns the editable fields of the joined piece (handles, types, segs, closed).
 */
export function joinEnds(a, endA, b, endB) {
  if (a === b) {
    // closing a ring: the dragged end coincides with the other end and is dropped
    const p = endA === 'end' ? a : reversed(a)
    const types = p.types.slice(0, -1)
    types[0] = 'smooth'
    return { handles: p.handles.slice(0, -1), types, segs: [...p.segs], closed: true }
  }
  const first = endA === 'end' ? a : reversed(a) // the joining end is its last point
  const second = endB === 'start' ? b : reversed(b) // the joining end is its first point
  return {
    handles: [...first.handles, ...second.handles.slice(1)],
    types: [...first.types.slice(0, -1), 'smooth', ...second.types.slice(1)],
    segs: [...first.segs, ...second.segs],
    closed: false,
  }
}

/** Move point p towards q by `distance`, but at most 40 % of the way. */
function pullTowards(p, q, distance) {
  const d = sub(q, p)
  const l = len(d)
  if (l < 1e-9) return p
  const step = Math.min(distance, 0.4 * l)
  return r2([p[0] + (d[0] / l) * step, p[1] + (d[1] / l) * step])
}

/**
 * Cut a piece at handle `i`. An open piece becomes two pieces, a ring becomes one open
 * piece. The point is duplicated and both new ends are pulled `gap` / 2 apart along the
 * path. Cutting at an open end is not possible and returns null.
 * Returns a list of editable fields (handles, types, segs, closed).
 */
export function cutAt(piece, i, gap = 6) {
  const n = piece.handles.length
  const { handles, types, segs } = piece
  const half = gap / 2
  if (piece.closed) {
    if (n < 3) return null
    // rotate so the ring starts and ends at the cut point
    const order = [...Array(n).keys()].map((k) => (i + k) % n)
    const h = [...order.map((k) => handles[k]), handles[i]]
    const ty = [...order.map((k) => types[k]), 'smooth']
    ty[0] = 'smooth'
    const sg = order.map((k) => segs[k])
    h[0] = pullTowards(h[0], h[1], half)
    h[n] = pullTowards(h[n], h[n - 1], half)
    return [{ handles: h, types: ty, segs: sg, closed: false }]
  }
  if (i <= 0 || i >= n - 1) return null
  const first = {
    handles: handles.slice(0, i + 1),
    types: [...types.slice(0, i), 'smooth'],
    segs: segs.slice(0, i),
    closed: false,
  }
  const second = {
    handles: handles.slice(i),
    types: ['smooth', ...types.slice(i + 1)],
    segs: segs.slice(i),
    closed: false,
  }
  first.handles[i] = pullTowards(handles[i], handles[i - 1], half)
  second.handles[0] = pullTowards(handles[i], handles[i + 1], half)
  return [first, second]
}

/** Whether `cutAt` is possible at handle i. */
export function canCutAt(piece, i) {
  return piece.closed ? piece.handles.length >= 3 : i > 0 && i < piece.handles.length - 1
}
