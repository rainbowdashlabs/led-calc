<script setup>
// SVG preview of the plan. Plan coordinates are mm with y pointing up.
// Views: 'front' (laying plan), 'back' (mirrored, as seen from behind) and
// 'result' (simulated finished sign without the font in the background).
// In edit mode the strip paths can be reshaped by dragging their control points.
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { buildPath } from '@/util/geometry'

const { t } = useI18n()

const props = defineProps({
  plan: Object,
  view: { type: String, default: 'front' },
  color: { type: String, default: '#ff3cac' },
  highlight: { type: Number, default: null },
  showDims: { type: Boolean, default: true },
  editMode: { type: Boolean, default: false },
  editPieces: { type: Array, default: null }, // [{ handles, pts, closed }]
  selected: { type: Number, default: null },
  wall: { type: String, default: '#0b0b0f' },
  zoom: { type: Number, default: 1 },
  draft: { type: Array, default: null }, // points of a piece being drawn
  snapTarget: { type: Object, default: null }, // end a dragged end would be joined to
})
const emit = defineEmits(['hover', 'select', 'move-handle', 'drag-end', 'insert-handle', 'toggle-point', 'point-menu', 'point-leave', 'draft-point', 'draft-finish', 'update:zoom'])

const W = computed(() => props.plan.plate.w)
const H = computed(() => props.plan.plate.h)
const sw = computed(() => props.plan.params.strip_width)
const holeR = computed(() => props.plan.params.hole_diameter / 2)
const back = computed(() => props.view === 'back')
const result = computed(() => props.view === 'result')
const cutView = computed(() => props.view === 'cut' && props.plan.cut)
const transform = computed(() => (back.value ? `matrix(-1 0 0 -1 ${W.value} ${H.value})` : `matrix(1 0 0 -1 0 ${H.value})`))
const tx = (x) => (back.value ? W.value - x : x)
const ty = (y) => H.value - y
const fs = computed(() => Math.max(6, Math.max(W.value, H.value) / 75) / zoom.value)

// ---- zoom & pan (zoom is controlled from outside via v-model:zoom)
const zoom = computed({ get: () => props.zoom, set: (v) => emit('update:zoom', Math.min(20, Math.max(0.5, v))) })
const center = reactive({ x: 0, y: 0 })
function resetView() {
  emit('update:zoom', 1)
  center.x = W.value / 2
  center.y = H.value / 2
}
// only reset when the plate size really changes (not on every recomputation)
watch(() => `${W.value}x${H.value}`, resetView, { immediate: true })
const pad = computed(() => Math.max(W.value, H.value) * 0.06)
const viewBox = computed(() => {
  const vw = (W.value + 2 * pad.value) / zoom.value
  const vh = (H.value + 2 * pad.value) / zoom.value
  return `${center.x - vw / 2} ${center.y - vh / 2} ${vw} ${vh}`
})
const svg = ref(null)
const layer = ref(null)
function screenToSvg(ev, el = svg.value) {
  const pt = svg.value.createSVGPoint()
  pt.x = ev.clientX
  pt.y = ev.clientY
  return pt.matrixTransform(el.getScreenCTM().inverse())
}
function onWheel(ev) {
  // zoom around the cursor: the point under the cursor stays where it is
  const p = screenToSvg(ev)
  const old = zoom.value
  const next = Math.min(20, Math.max(0.5, old * Math.exp(-Math.sign(ev.deltaY) * Math.min(Math.abs(ev.deltaY), 60) * 0.004)))
  if (next === old) return
  center.x = p.x + (center.x - p.x) * (old / next)
  center.y = p.y + (center.y - p.y) * (old / next)
  zoom.value = next
}
let pan = null
function onBgDown(ev) {
  if (ev.button !== 0 && ev.button !== 1) return
  pan = { x: ev.clientX, y: ev.clientY, cx: center.x, cy: center.y }
  ev.currentTarget.setPointerCapture(ev.pointerId)
}
function onBgMove(ev) {
  if (drawing.value) cursor.value = toPlan(ev)
  if (drag) return onDragMove(ev)
  if (!pan) return
  const r = svg.value.getBoundingClientRect()
  const vb = viewBox.value.split(' ').map(Number)
  const s = Math.max(vb[2] / r.width, vb[3] / r.height)
  center.x = pan.cx - (ev.clientX - pan.x) * s
  center.y = pan.cy - (ev.clientY - pan.y) * s
}
function onBgUp(ev) {
  if (drag) return onDragEnd(ev)
  const click = pan && Math.hypot(ev.clientX - pan.x, ev.clientY - pan.y) < 3
  pan = null
  if (!click || !props.editMode) return
  if (drawing.value) onDraftClick(ev)
  else emit('select', null)
}

// ---- drawing a new piece
const drawing = computed(() => props.editMode && props.draft !== null)
const cursor = ref(null)
const toPlan = (ev) => {
  const p = screenToSvg(ev, layer.value)
  return [Math.round(p.x * 100) / 100, Math.round(p.y * 100) / 100]
}
/** The first point closes the piece when it is clicked again. */
const closable = computed(() => drawing.value && props.draft.length >= 3)
function nearFirst(xy) {
  const first = props.draft[0]
  return first && Math.hypot(first[0] - xy[0], first[1] - xy[1]) < 4 * hs(null)
}
function onDraftClick(ev) {
  const xy = toPlan(ev)
  if (closable.value && nearFirst(xy)) emit('draft-finish', true)
  else emit('draft-point', xy)
}
function onDraftDblClick() {
  if (drawing.value) emit('draft-finish', false)
}
const draftPath = computed(() => {
  if (!drawing.value || props.draft.length < 2) return []
  return buildPath(props.draft, null, null, false)
})

// ---- editing
let drag = null
function onHandleDown(ev, pi, hi) {
  if (drawing.value) return
  ev.stopPropagation()
  if (ev.button === 2) return
  drag = { pi, hi, moved: false }
  emit('select', pi)
  svg.value.setPointerCapture(ev.pointerId)
}
function onDragMove(ev) {
  const p = screenToSvg(ev, layer.value)
  drag.moved = true
  emit('move-handle', drag.pi, drag.hi, [Math.round(p.x * 100) / 100, Math.round(p.y * 100) / 100])
}
function onDragEnd() {
  if (drag?.moved) emit('drag-end', drag.pi, drag.hi)
  drag = null
}
function onPieceDblClick(ev, pi) {
  ev.stopPropagation()
  const p = screenToSvg(ev, layer.value)
  emit('insert-handle', pi, [p.x, p.y])
}
function onHandleContext(ev, pi, hi) {
  ev.preventDefault()
  emit('point-menu', pi, hi, ev.clientX, ev.clientY, true)
}
function onHandleDblClick(ev, pi, hi) {
  ev.stopPropagation()
  emit('toggle-point', pi, hi)
}
function onHandleEnter(ev, pi, hi) {
  if (!drag && !drawing.value) emit('point-menu', pi, hi, ev.clientX, ev.clientY, false)
}

const pieces = computed(() => {
  if (props.editMode && props.editPieces) {
    return props.editPieces.map((e, i) => ({ no: i + 1, pts: e.pts, closed: e.closed, role: e.role, violations: [], smoothed: [], idx: i }))
  }
  return props.plan.pieces.map((p, i) => ({ ...p, idx: i }))
})

const pts = (arr) => arr.map(([x, y]) => `${x},${y}`).join(' ')
const ringPath = (rings) => rings.map((r) => 'M' + r.map(([x, y]) => `${x},${y}`).join('L') + 'Z').join('')
const holeHasOut = (h) => h.uses.some((u) => u[1] === 'out')
const hs = (pi) => (props.selected === pi ? 2.4 : 1.7) / Math.sqrt(zoom.value)
const fmt = (mm) => `${(mm / 10).toLocaleString('de-DE', { maximumFractionDigits: 1 })} cm`

defineExpose({ resetView })
</script>

<template>
  <svg
    ref="svg" :viewBox="viewBox" class="h-full w-full touch-none select-none" :class="editMode ? 'cursor-crosshair' : 'cursor-grab'" @dblclick="onDraftDblClick"
    @wheel.prevent="onWheel" @pointerdown="onBgDown" @pointermove="onBgMove" @pointerup="onBgUp" @contextmenu.prevent
  >
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur :stdDeviation="sw * 0.9" result="b" />
        <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur :stdDeviation="sw * 2.5" result="b2" />
        <feGaussianBlur in="SourceGraphic" :stdDeviation="sw * 0.6" result="b1" />
        <feMerge><feMergeNode in="b2" /><feMergeNode in="b2" /><feMergeNode in="b1" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" stroke="#a855f7" stroke-width="1" />
      </pattern>
    </defs>

    <g ref="layer" :transform="transform">
      <rect
        x="0" y="0" :width="W" :height="H" :rx="plan.plate.corner"
        :fill="result ? wall : back ? '#18181b' : '#111114'" :stroke="result ? '#27272a' : '#52525b'" stroke-width="1"
      />

      <!-- ===== cut-outs (channels and bridges) ===== -->
      <template v-if="cutView">
        <rect x="0" y="0" :width="W" :height="H" :rx="plan.plate.corner" fill="#a16207" fill-opacity="0.35" stroke="#ca8a04" stroke-width="1" />
        <path v-for="(rings, i) in plan.cut.channels" :key="'ch' + i" :d="ringPath(rings)" fill-rule="evenodd" fill="#0a0a0a" stroke="#fde68a" stroke-width="0.5" />
        <path v-for="(rings, i) in plan.cut.bridges" :key="'br' + i" :d="ringPath(rings)" fill="#22c55e" stroke="#bbf7d0" stroke-width="0.4" />
        <polyline v-for="p in pieces" :key="'cl' + p.no" :points="pts(p.closed ? [...p.pts, p.pts[0]] : p.pts)" fill="none" :stroke="color" stroke-width="0.6" stroke-opacity="0.8" />
      </template>

      <!-- ===== simulated result ===== -->
      <template v-else-if="result">
        <g filter="url(#glow-strong)">
          <component
            :is="p.closed ? 'polygon' : 'polyline'" v-for="p in pieces" :key="'r' + p.no" :points="pts(p.pts)"
            fill="none" :stroke="color" :stroke-width="sw" stroke-linecap="round" stroke-linejoin="round"
          />
        </g>
        <component
          :is="p.closed ? 'polygon' : 'polyline'" v-for="p in pieces" :key="'rc' + p.no" :points="pts(p.pts)"
          fill="none" stroke="#fff" stroke-opacity="0.55" :stroke-width="sw * 0.35" stroke-linecap="round" stroke-linejoin="round"
        />
      </template>

      <template v-else>
        <!-- letters -->
        <path
          v-for="(rings, i) in plan.letters" :key="'l' + i" :d="ringPath(rings)" fill-rule="evenodd"
          :fill="back ? 'none' : '#27272a'" stroke="#3f3f46" stroke-width="0.6" :stroke-dasharray="back ? '3 3' : null"
        />
        <polyline v-for="(s, i) in plan.strokes" :key="'s' + i" :points="pts(s)" fill="none" stroke="#3f3f46" stroke-width="1" />

        <!-- routes behind the plate (follow the bend radius) -->
        <polyline
          v-for="(l, i) in plan.links" :key="'k' + i" :points="pts(l.path || [l.a, l.b])" fill="none"
          :stroke="l.kind === 'strip' ? (back ? color : '#f59e0b') : '#38bdf8'"
          :stroke-width="back ? (l.kind === 'strip' ? sw : 2) : 1.2" :stroke-dasharray="back ? null : '6 4'"
          :stroke-opacity="editMode ? 0.3 : back ? 0.9 : 0.75" stroke-linecap="round" stroke-linejoin="round"
        />

        <!-- front: strip pieces -->
        <template v-if="!back">
          <g filter="url(#glow)">
            <component
              :is="p.closed ? 'polygon' : 'polyline'" v-for="p in pieces" :key="'p' + p.no" :points="pts(p.pts)"
              fill="none" :stroke="color" :stroke-width="sw" stroke-linecap="round" stroke-linejoin="round"
              :stroke-opacity="(highlight && highlight !== p.no) || (editMode && selected !== null && selected !== p.idx) ? 0.3 : 0.95"
              @mouseenter="emit('hover', p.no)" @mouseleave="emit('hover', null)"
              @pointerdown.stop="editMode && !drawing && emit('select', p.idx)" @dblclick="editMode && !drawing && onPieceDblClick($event, p.idx)"
            />
          </g>
          <component
            :is="p.closed ? 'polygon' : 'polyline'" v-for="p in pieces" :key="'c' + p.no" :points="pts(p.pts)"
            fill="none" stroke="#fff" stroke-opacity="0.7" :stroke-width="sw * 0.12" pointer-events="none"
          />
        </template>
        <template v-else>
          <component
            :is="p.closed ? 'polygon' : 'polyline'" v-for="p in pieces" :key="'b' + p.no" :points="pts(p.pts)"
            fill="none" stroke="#71717a" :stroke-width="sw" stroke-opacity="0.25" stroke-linejoin="round"
          />
        </template>

        <!-- holes -->
        <g v-for="h in plan.holes" :key="'h' + h.no" :opacity="editMode ? 0.35 : 1">
          <circle :cx="h.x" :cy="h.y" :r="holeR" fill="#000" :stroke="holeHasOut(h) ? '#f59e0b' : '#22c55e'" stroke-width="1.2" />
          <line :x1="h.x - holeR * 0.6" :y1="h.y" :x2="h.x + holeR * 0.6" :y2="h.y" stroke="#a1a1aa" stroke-width="0.4" />
          <line :x1="h.x" :y1="h.y - holeR * 0.6" :x2="h.x" :y2="h.y + holeR * 0.6" stroke="#a1a1aa" stroke-width="0.4" />
        </g>

        <!-- strips crossing behind the plate -->
        <template v-if="back">
          <circle v-for="(c, j) in plan.back_crossings || []" :key="'x' + j" :cx="c.x" :cy="c.y" :r="sw * 1.6" fill="none" stroke="#ef4444" stroke-width="1.5" />
        </template>

        <!-- problems -->
        <template v-if="!back && !editMode">
          <g v-for="p in plan.pieces" :key="'v' + p.no">
            <circle v-for="(v, j) in p.violations" :key="j" :cx="v.x" :cy="v.y" :r="sw * 1.4" fill="none" stroke="#ef4444" stroke-width="1.2" />
            <circle v-for="(v, j) in p.smoothed || []" :key="'sm' + j" :cx="v.x" :cy="v.y" :r="sw * 1.4" fill="none" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2 1.5" />
          </g>
          <circle v-for="(m, j) in plan.markers" :key="'m' + j" :cx="m.x" :cy="m.y" :r="sw * 1.6" fill="url(#hatch)" stroke="#e879f9" stroke-width="1.2" />
          <circle v-for="(o, j) in plan.omitted" :key="'o' + j" :cx="o.x" :cy="o.y" :r="sw" fill="none" stroke="#a1a1aa" stroke-dasharray="2 2" />
        </template>

        <!-- edit handles -->
        <template v-if="editMode && editPieces">
          <g v-for="(e, pi) in editPieces" :key="'e' + pi">
            <template v-for="(hd, hi) in e.handles" :key="hi">
              <rect
                v-if="e.types?.[hi] === 'corner'" :x="hd[0] - hs(pi)" :y="hd[1] - hs(pi)" :width="2 * hs(pi)" :height="2 * hs(pi)"
                :fill="selected === pi ? '#fff' : '#f9a8d4'" stroke="#be185d" :stroke-width="0.6 / Math.sqrt(zoom)" class="cursor-move"
                @pointerdown="onHandleDown($event, pi, hi)" @contextmenu="onHandleContext($event, pi, hi)"
                @dblclick="onHandleDblClick($event, pi, hi)" @mouseenter="onHandleEnter($event, pi, hi)" @mouseleave="emit('point-leave')"
              />
              <circle
                v-else :cx="hd[0]" :cy="hd[1]" :r="hs(pi) * 1.1"
                :fill="selected === pi ? '#fff' : '#f9a8d4'" stroke="#be185d" :stroke-width="0.6 / Math.sqrt(zoom)" class="cursor-move"
                @pointerdown="onHandleDown($event, pi, hi)" @contextmenu="onHandleContext($event, pi, hi)"
                @dblclick="onHandleDblClick($event, pi, hi)" @mouseenter="onHandleEnter($event, pi, hi)" @mouseleave="emit('point-leave')"
              />
            </template>
          </g>
        </template>

        <!-- end that a dragged end would be joined to -->
        <circle
          v-if="editMode && snapTarget" :cx="snapTarget.xy[0]" :cy="snapTarget.xy[1]" :r="4 * hs(null)"
          fill="none" stroke="#22c55e" :stroke-width="1.2 / Math.sqrt(zoom)" pointer-events="none"
        />

        <!-- piece being drawn -->
        <template v-if="drawing">
          <polyline v-if="draftPath.length" :points="pts(draftPath)" fill="none" :stroke="color" :stroke-width="sw" stroke-opacity="0.6" stroke-linecap="round" stroke-linejoin="round" pointer-events="none" />
          <line
            v-if="draft.length && cursor" :x1="draft.at(-1)[0]" :y1="draft.at(-1)[1]" :x2="cursor[0]" :y2="cursor[1]"
            :stroke="color" :stroke-width="0.8 / Math.sqrt(zoom)" stroke-dasharray="3 2" pointer-events="none"
          />
          <circle
            v-for="(pt, i) in draft" :key="'d' + i" :cx="pt[0]" :cy="pt[1]" :r="(i === 0 && closable ? 2.2 : 1.4) * hs(null)"
            :fill="i === 0 && closable ? '#22c55e' : '#fff'" stroke="#be185d" :stroke-width="0.6 / Math.sqrt(zoom)" pointer-events="none"
          />
        </template>

        <!-- feed point -->
        <circle :cx="plan.feed.x" :cy="plan.feed.y" :r="holeR * 1.2" fill="#22c55e" />
      </template>
    </g>

    <!-- labels and dimensions (screen orientation, never mirrored) -->
    <g v-if="!result && !cutView" font-family="ui-sans-serif, system-ui" pointer-events="none">
      <g v-for="p in pieces" :key="'t' + p.no">
        <circle :cx="tx(p.pts[0][0])" :cy="ty(p.pts[0][1])" :r="fs * 0.75" fill="#09090b" stroke="#e4e4e7" stroke-width="0.5" />
        <text :x="tx(p.pts[0][0])" :y="ty(p.pts[0][1])" text-anchor="middle" dominant-baseline="central" fill="#fafafa" :font-size="fs * 0.8">{{ p.no }}</text>
      </g>
      <text :x="tx(plan.feed.x)" :y="ty(plan.feed.y) + fs * 1.6" text-anchor="middle" fill="#22c55e" :font-size="fs * 0.8">{{ t('einspeisung') }}</text>
    </g>
    <g v-if="showDims" font-family="ui-sans-serif, system-ui" pointer-events="none" :font-size="fs * 0.85" fill="#a1a1aa" stroke-width="0.6">
      <!-- plate -->
      <line :x1="0" :y1="-pad * 0.45" :x2="W" :y2="-pad * 0.45" stroke="#71717a" />
      <line :x1="0" :y1="-pad * 0.6" :x2="0" :y2="-pad * 0.3" stroke="#71717a" />
      <line :x1="W" :y1="-pad * 0.6" :x2="W" :y2="-pad * 0.3" stroke="#71717a" />
      <text :x="W / 2" :y="-pad * 0.55" text-anchor="middle">{{ t('platte') }} {{ fmt(W) }}</text>
      <line :x1="-pad * 0.45" :y1="0" :x2="-pad * 0.45" :y2="H" stroke="#71717a" />
      <line :x1="-pad * 0.6" :y1="0" :x2="-pad * 0.3" :y2="0" stroke="#71717a" />
      <line :x1="-pad * 0.6" :y1="H" :x2="-pad * 0.3" :y2="H" stroke="#71717a" />
      <text :x="-pad * 0.55" :y="H / 2" text-anchor="middle" :transform="`rotate(-90 ${-pad * 0.55} ${H / 2})`">{{ fmt(H) }}</text>
      <!-- lettering -->
      <template v-if="plan.bounds">
        <line :x1="tx(plan.bounds.x0)" :y1="H + pad * 0.45" :x2="tx(plan.bounds.x1)" :y2="H + pad * 0.45" stroke="#f472b6" />
        <line :x1="tx(plan.bounds.x0)" :y1="H + pad * 0.3" :x2="tx(plan.bounds.x0)" :y2="H + pad * 0.6" stroke="#f472b6" />
        <line :x1="tx(plan.bounds.x1)" :y1="H + pad * 0.3" :x2="tx(plan.bounds.x1)" :y2="H + pad * 0.6" stroke="#f472b6" />
        <text :x="W / 2" :y="H + pad * 0.85" text-anchor="middle" fill="#f9a8d4">{{ t('schrift') }} {{ fmt(plan.bounds.x1 - plan.bounds.x0) }}</text>
        <line :x1="W + pad * 0.45" :y1="ty(plan.bounds.y1)" :x2="W + pad * 0.45" :y2="ty(plan.bounds.y0)" stroke="#f472b6" />
        <line :x1="W + pad * 0.3" :y1="ty(plan.bounds.y1)" :x2="W + pad * 0.6" :y2="ty(plan.bounds.y1)" stroke="#f472b6" />
        <line :x1="W + pad * 0.3" :y1="ty(plan.bounds.y0)" :x2="W + pad * 0.6" :y2="ty(plan.bounds.y0)" stroke="#f472b6" />
        <text :x="W + pad * 0.8" :y="H / 2" text-anchor="middle" fill="#f9a8d4" :transform="`rotate(90 ${W + pad * 0.8} ${H / 2})`">{{ fmt(plan.bounds.y1 - plan.bounds.y0) }}</text>
      </template>
    </g>
  </svg>
</template>
