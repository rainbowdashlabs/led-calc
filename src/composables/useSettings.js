// All user settings (UI units), persisted in localStorage, and their mapping to the
// parameters of the Python core (singleton state).
import { reactive, watch } from 'vue'

export const DEFAULT_SETTINGS = {
  text: 'Hallo', fontId: 'pacifico', mode: 'contour', fontWeight: null,
  capHeightCm: 15, trackingMm: 0, widthPct: 100, lineSpacing: 1.5, align: 'center',
  stripWidth: 7, bendRadiusCm: 3, contourOffset: null, hersheyStroke: null,
  autoSmooth: false, smoothRadiusCm: null, smoothMaxDev: 8,
  dotMode: 'through', umlautStyle: 'dots',
  marginCm: 4, plateCorner: 10, plateThickness: 5, holeDiameter: 10,
  connection: 'strip', feed: 'bottom-left', passExtra: 10, pieceAllowance: 0, cableReserve: 50,
  cutUnit: 10, rollLengthM: 5, paper: 'A4', parts: ['overview', 'front', 'back'],
  frame: false, frameInsetMm: null, frameCorners: 'round',
  cutMode: 'none', cutTolerance: 1, cutDepth: null, bridgeWidth: 8,
}

const STORAGE_KEY = 'led-neon-planer:v1'
const settings = reactive({ ...DEFAULT_SETTINGS })
try {
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
  if (saved) Object.assign(settings, saved)
} catch { /* storage unavailable */ }
watch(settings, () => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)) } catch { /* ignore */ } }, { deep: true })

const num = (v) => (v === '' || v === null || v === undefined || Number.isNaN(v) ? null : v)

// parameters that do not change the strip geometry; hand edits survive changes of these
const NON_GEOMETRY = ['lang', 'connection', 'feed', 'plate_thickness', 'hole_diameter', 'pass_extra', 'piece_allowance',
  'cable_reserve', 'cut_unit', 'roll_length', 'plate_corner', 'dot_mode', 'cut_mode', 'cut_tolerance', 'cut_depth', 'bridge_width']

export function useSettings() {
  /** Parameters for the Python core (mm). `fontKind` and `weight` come from the font catalogue. */
  function params({ lang, fontKind, weight }) {
    const s = settings
    return {
      lang, text: s.text, font_kind: fontKind, mode: s.mode, font_weight: weight,
      cap_height: s.capHeightCm * 10, tracking: s.trackingMm, width_scale: s.widthPct / 100,
      line_spacing: s.lineSpacing, align: s.align,
      strip_width: s.stripWidth, bend_radius: s.bendRadiusCm * 10,
      contour_offset: num(s.contourOffset), hershey_stroke: num(s.hersheyStroke),
      auto_smooth: s.autoSmooth, smooth_radius: num(s.smoothRadiusCm) === null ? null : s.smoothRadiusCm * 10, smooth_max_dev: s.smoothMaxDev,
      dot_mode: s.dotMode, umlaut_style: s.umlautStyle,
      margin: s.marginCm * 10, plate_corner: s.plateCorner, plate_thickness: s.plateThickness, hole_diameter: s.holeDiameter,
      connection: s.connection, feed: s.feed, pass_extra: s.passExtra, piece_allowance: s.pieceAllowance,
      cable_reserve: s.cableReserve, cut_unit: s.cutUnit, roll_length: s.rollLengthM * 1000,
      frame: s.frame, frame_inset: num(s.frameInsetMm), frame_corners: s.frameCorners,
      cut_mode: s.cutMode, cut_tolerance: s.cutTolerance, cut_depth: num(s.cutDepth), bridge_width: s.bridgeWidth,
    }
  }

  /** Identifies the strip geometry; hand edits are only valid for one signature. */
  function geometrySignature(p) {
    const q = { ...p }
    for (const k of NON_GEOMETRY) delete q[k]
    return JSON.stringify([settings.fontId, q])
  }

  function reset(values) {
    Object.assign(settings, { ...DEFAULT_SETTINGS, ...values })
  }

  return { settings, params, geometrySignature, reset }
}
