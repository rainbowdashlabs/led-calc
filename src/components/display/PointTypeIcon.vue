<script setup>
/**
 * Pictogram of an edit point type: how the path runs into and out of the point (dot).
 * Straight segments are drawn straight, curves curved; a smooth joint continues the
 * direction, a corner has a visible kink.
 */
const SHAPES = {
  round: 'M3 19C5 9 9 6 12 6s7 3 9 13',
  corner: 'M3 19 12 6l9 13',
  line_curve_tangent: 'M3 19 12 6c3-4.5 9-3 9 8',
  curve_line_tangent: 'M3 14c0-11 6-12.5 9-8l9 13',
  line_curve_corner: 'M3 19 12 6c5 0 9 5 9 13',
  curve_line_corner: 'M3 19C3 11 7 6 12 6l9 13',
  curve_curve_corner: 'M3 19C3 11 7 6 12 6c5 0 9 5 9 13',
}

defineProps({
  type: { type: String, required: true },
  size: { type: Number, default: 28 },
})
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path :d="SHAPES[type]" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="12" cy="6" r="2.4" class="fill-pink-400" />
  </svg>
</template>
