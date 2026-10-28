<script setup>
import { useI18n } from 'vue-i18n'
import AppIcon from '@/components/display/AppIcon.vue'
import PointTypeIcon from '@/components/display/PointTypeIcon.vue'
import { useEditor } from '@/composables/useEditor'

/** How the path runs through an edit point; names are shown as tooltips. */
const PRESETS = [
  ['round', 'rund_spline'],
  ['corner', 'ecke_gerade_gerade'],
  ['line_curve_tangent', 'gerade_bogen_tangential'],
  ['curve_line_tangent', 'bogen_gerade_tangential'],
  ['line_curve_corner', 'gerade_bogen_eckig'],
  ['curve_line_corner', 'bogen_gerade_eckig'],
  ['curve_curve_corner', 'bogen_bogen_eckig'],
]

const { t } = useI18n()
const editor = useEditor()
const menu = editor.menu
</script>

<template>
  <Teleport to="body">
    <div
      v-if="menu.open && editor.active.value"
      class="fixed z-40 grid grid-cols-4 gap-1 rounded-lg border border-zinc-700 bg-zinc-900/95 p-1.5 shadow-2xl shadow-black/60 backdrop-blur"
      :style="{ left: `${menu.x + 12}px`, top: `${menu.y + 12}px` }"
      role="menu"
      :aria-label="t('punkt_menue')"
      @mouseenter="menu.hovered = true"
      @mouseleave="menu.hovered = false; editor.leaveMenu()"
    >
      <button
        v-for="[key, label] in PRESETS"
        :key="key"
        type="button"
        role="menuitemradio"
        :aria-checked="editor.currentPreset.value === key"
        :aria-label="t(label)"
        :title="t(label)"
        class="menu-tile"
        :class="editor.currentPreset.value === key ? 'bg-pink-500/20 text-pink-200 ring-1 ring-pink-500/70' : 'text-zinc-300'"
        @click="editor.applyPreset(menu.piece, menu.handle, key)"
      >
        <PointTypeIcon :type="key" />
      </button>
      <button
        type="button"
        role="menuitem"
        :aria-label="t('punkt_loeschen')"
        :title="t('punkt_loeschen')"
        class="menu-tile text-red-300 hover:!bg-red-500/15"
        @click="editor.removeHandle(menu.piece, menu.handle)"
      >
        <AppIcon name="trash" :size="20" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
@reference "@/style.css";

.menu-tile {
  @apply grid h-10 w-10 place-items-center rounded-md transition hover:bg-pink-500/15;
}
</style>
