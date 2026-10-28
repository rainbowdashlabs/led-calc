// Editing session for strip paths: handles with a type ('smooth' | 'corner') and segments
// ('curve' | 'line'). While editing, `pieces` is the source of truth; every change is
// committed as manual edits, recorded for undo / redo and the plan is recomputed (singleton).
import { computed, reactive, ref } from 'vue'
import { buildPath, editableFrom, nearestSegment, POINT_PRESETS, presetOf } from '@/util/geometry'
import { createHistory } from '@/util/history'
import { useManualEdits } from './useManualEdits'
import { usePlanner } from './usePlanner'
import { usePreviewState, VIEWS } from './usePreviewState'

const active = ref(false)
const pieces = ref(null)
const selected = ref(null)
const menu = reactive({ open: false, piece: null, handle: null, x: 0, y: 0, pinned: false, hovered: false })
let menuTimer = null
const history = createHistory({ limit: 100 })
const canUndo = ref(false)
const canRedo = ref(false)

const MENU_DELAY_MS = 350
const round1 = ([x, y]) => [Math.round(x * 10) / 10, Math.round(y * 10) / 10] // 0.1 mm keeps share codes short
const round2 = ([x, y]) => [Math.round(x * 100) / 100, Math.round(y * 100) / 100]
const meta = (p) => ({ char: p.char, glyph: p.glyph, role: p.role, inner: p.inner, butt_start: p.butt_start, butt_end: p.butt_end })

export function useEditor() {
  const manual = useManualEdits()
  const { plan, signature, schedule } = usePlanner()
  const preview = usePreviewState()

  function start() {
    if (!plan.value) return
    preview.view = VIEWS.FRONT
    // continue earlier hand edits if there are any, else start from the computed plan
    const source = manual.pieces.value
      ? manual.pieces.value.map((m) => ({ ...m, ...(m.handles ? {} : editableFrom(m.pts, m.closed)) }))
      : plan.value.pieces.map((p) => ({ ...meta(p), pts: p.pts, closed: p.closed, edited: false, ...editableFrom(p.pts, p.closed) }))
    pieces.value = JSON.parse(JSON.stringify(source))
    selected.value = null
    active.value = true
    history.reset(snapshot())
    syncHistory()
  }

  function finish() {
    active.value = false
    selected.value = null
    closeMenu()
  }

  function discard() {
    manual.clear()
    finish()
    schedule()
  }

  /** Take over the current pieces as manual edits and remember them for undo. */
  function commit() {
    history.record(snapshot())
    syncHistory()
    publish()
  }

  function undo() {
    restore(history.undo())
  }

  function redo() {
    restore(history.redo())
  }

  function restore(state) {
    if (state === null) return
    pieces.value = JSON.parse(state)
    selected.value = null
    closeMenu()
    syncHistory()
    publish()
  }

  const snapshot = () => JSON.stringify(pieces.value)

  function syncHistory() {
    canUndo.value = history.canUndo
    canRedo.value = history.canRedo
  }

  /** Hand the pieces to the planner as manual edits and recompute. */
  function publish() {
    manual.commit(pieces.value.map((e) => ({
      ...meta(e), pts: e.pts.map(round1), closed: e.closed, edited: e.edited,
      handles: e.handles.map(round1), types: [...e.types], segs: [...e.segs],
    })), signature.value)
    schedule()
  }

  function rebuild(piece) {
    piece.pts = buildPath(piece.handles, piece.types, piece.segs, piece.closed)
    piece.edited = true
  }

  function moveHandle(pi, hi, xy) {
    const piece = pieces.value[pi]
    piece.handles[hi] = xy
    rebuild(piece)
    closeMenu()
  }

  function insertHandle(pi, xy) {
    const piece = pieces.value[pi]
    const { index } = nearestSegment(piece.handles, piece.closed, xy)
    piece.handles.splice(index + 1, 0, round2(xy))
    piece.types.splice(index + 1, 0, 'smooth')
    piece.segs.splice(index + 1, 0, piece.segs[index] ?? 'curve')
    rebuild(piece)
    commit()
  }

  function removeHandle(pi, hi) {
    const piece = pieces.value[pi]
    if (piece.handles.length <= (piece.closed ? 3 : 2)) return
    piece.handles.splice(hi, 1)
    piece.types.splice(hi, 1)
    piece.segs.splice(Math.min(hi, piece.segs.length - 1), 1)
    rebuild(piece)
    commit()
    closeMenu()
  }

  /** Indices of the segments ending at / starting from handle hi (null at open ends). */
  function adjacentSegments(piece, hi) {
    const n = piece.handles.length
    const count = piece.closed ? n : n - 1
    const before = piece.closed ? (hi - 1 + n) % n : hi - 1
    return { incoming: before >= 0 ? before : null, outgoing: hi < count ? hi : null }
  }

  function applyPreset(pi, hi, key) {
    const piece = pieces.value[pi]
    const [type, incomingType, outgoingType] = POINT_PRESETS[key]
    const { incoming, outgoing } = adjacentSegments(piece, hi)
    piece.types[hi] = type
    if (incoming !== null) piece.segs[incoming] = incomingType
    if (outgoing !== null) piece.segs[outgoing] = outgoingType
    rebuild(piece)
    commit()
  }

  function togglePoint(pi, hi) {
    applyPreset(pi, hi, pieces.value[pi].types[hi] === 'corner' ? 'round' : 'corner')
  }

  function deleteSelected() {
    if (selected.value === null) return
    pieces.value.splice(selected.value, 1)
    selected.value = null
    commit()
  }

  // ---- point menu: opens on hover (delayed) or right click (pinned)
  function openMenu(pi, hi, x, y, pinned) {
    clearTimeout(menuTimer)
    const open = () => Object.assign(menu, { open: true, piece: pi, handle: hi, x, y, pinned })
    if (pinned) open()
    else menuTimer = setTimeout(open, MENU_DELAY_MS)
  }
  function leaveMenu() {
    clearTimeout(menuTimer)
    if (!menu.pinned) menuTimer = setTimeout(() => { if (!menu.hovered) closeMenu() }, MENU_DELAY_MS)
  }
  function closeMenu() {
    clearTimeout(menuTimer)
    Object.assign(menu, { open: false, pinned: false })
  }
  const currentPreset = computed(() => (menu.open && pieces.value?.[menu.piece] ? presetOf(pieces.value[menu.piece], menu.handle) : null))

  return {
    active, pieces, selected, menu, currentPreset, canUndo, canRedo,
    start, finish, discard, commit, undo, redo,
    moveHandle, insertHandle, removeHandle, applyPreset, togglePoint, deleteSelected,
    openMenu, leaveMenu, closeMenu,
  }
}
