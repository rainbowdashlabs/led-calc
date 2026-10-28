import { describe, expect, it } from 'vitest'
import { canCutAt, cutAt, joinEnds, reversed } from './geometry'

const piece = (handles) => ({
  handles,
  types: handles.map(() => 'smooth'),
  segs: handles.slice(1).map(() => 'curve'),
  closed: false,
})

describe('joinEnds', () => {
  const a = piece([[0, 0], [10, 0]])
  const b = piece([[10, 0], [20, 5], [30, 0]])

  it('joins the end of one piece to the start of another', () => {
    const j = joinEnds(a, 'end', b, 'start')
    expect(j.handles).toEqual([[0, 0], [10, 0], [20, 5], [30, 0]])
    expect(j.segs).toHaveLength(3)
    expect(j.types).toHaveLength(4)
    expect(j.closed).toBe(false)
  })

  it('reverses pieces as needed so the chosen ends meet', () => {
    const j = joinEnds(reversed(a), 'start', reversed(b), 'end')
    expect(j.handles).toEqual([[0, 0], [10, 0], [20, 5], [30, 0]])
  })

  it('makes the meeting point smooth even if it was a corner', () => {
    const cornerEnd = { ...a, types: ['smooth', 'corner'] }
    expect(joinEnds(cornerEnd, 'end', b, 'start').types[1]).toBe('smooth')
  })

  it('closes a piece when its ends are joined', () => {
    const open = piece([[0, 0], [10, 0], [10, 10], [0, 0]])
    const ring = joinEnds(open, 'end', open, 'start')
    expect(ring.closed).toBe(true)
    expect(ring.handles).toHaveLength(3)
    expect(ring.segs).toHaveLength(3) // a ring has as many segments as points
  })
})

describe('cutAt', () => {
  const open = piece([[0, 0], [10, 0], [20, 0], [30, 0]])

  it('splits an open piece into two at an inner point and pulls the ends apart', () => {
    const [a, b] = cutAt(open, 2, 6)
    expect(a.handles).toEqual([[0, 0], [10, 0], [17, 0]])
    expect(b.handles).toEqual([[23, 0], [30, 0]])
    expect(a.segs).toHaveLength(2)
    expect(b.segs).toHaveLength(1)
    expect(a.types.at(-1)).toBe('smooth')
  })

  it('cannot cut at an open end', () => {
    expect(cutAt(open, 0)).toBeNull()
    expect(cutAt(open, 3)).toBeNull()
    expect(canCutAt(open, 0)).toBe(false)
    expect(canCutAt(open, 1)).toBe(true)
  })

  it('opens a ring at the cut point', () => {
    const ring = { ...piece([[0, 0], [10, 0], [10, 10], [0, 10]]), segs: ['curve', 'curve', 'line', 'curve'], closed: true }
    const [opened] = cutAt(ring, 2, 4)
    expect(opened.closed).toBe(false)
    expect(opened.handles).toHaveLength(5)
    expect(opened.segs).toEqual(['line', 'curve', 'curve', 'curve'])
    expect(opened.handles[0]).toEqual([8, 10])   // pulled towards the next point
    expect(opened.handles[4]).toEqual([10, 8])   // pulled towards the previous point
  })
})
