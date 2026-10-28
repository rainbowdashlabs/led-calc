<script setup>
import { computed, ref } from 'vue'
import BaseCard from '@/components/container/BaseCard.vue'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useEditor } from '@/composables/useEditor'
import { usePlanner } from '@/composables/usePlanner'
import { usePreviewState } from '@/composables/usePreviewState'
import { useProgressLabel } from '@/composables/useProgressLabel'
import EditorBar from './EditorBar.vue'
import PlanPreview from './PlanPreview.vue'
import PointMenu from './PointMenu.vue'
import PreviewLegend from './PreviewLegend.vue'
import PreviewToolbar from './PreviewToolbar.vue'
import ProgressOverlay from './ProgressOverlay.vue'

/** Connects the purely presentational PlanPreview with planner, editor and view state. */
const { plan, progress } = usePlanner()
const preview = usePreviewState()
const editor = useEditor()
const progressLabel = useProgressLabel()
const { isCoarsePointer } = useBreakpoint()
const svg = ref(null)
// the stage takes the plate's aspect ratio (plus room for the dimensions), bounded by the screen
const stageStyle = computed(() => (plan.value ? { aspectRatio: `${plan.value.plate.w * 1.12} / ${plan.value.plate.h * 1.12 + plan.value.plate.w * 0.05}` } : {}))
</script>

<template>
  <BaseCard :padded="false">
    <PreviewToolbar @fit="svg?.resetView()" />
    <EditorBar v-if="editor.active.value" />
    <div class="stage" :style="stageStyle">
      <ProgressOverlay :active="progress.active" :fraction="progress.fraction" :label="progressLabel" />
      <PlanPreview
        ref="svg"
        v-model:zoom="preview.zoom"
        :plan="plan"
        :view="preview.view"
        :color="preview.neonColor"
        :wall="preview.wallColor"
        :highlight="preview.hover"
        :show-dims="preview.showDims && preview.view !== 'result'"
        :edit-mode="editor.active.value"
        :edit-pieces="editor.pieces.value"
        :selected="editor.selected.value"
        :draft="editor.draft.value"
        :snap-target="editor.snapTarget.value"
        :coarse-pointer="isCoarsePointer"
        @hover="preview.hover = $event"
        @select="editor.selected.value = $event"
        @move-handle="editor.moveHandle"
        @drag-end="editor.dropHandle"
        @insert-handle="editor.insertHandle"
        @toggle-point="editor.togglePoint"
        @point-menu="editor.openMenu"
        @point-leave="editor.leaveMenu"
        @draft-point="editor.addDraftPoint"
        @draft-finish="editor.finishDrawing"
      />
    </div>
    <PreviewLegend :plan="plan" />
    <PointMenu />
  </BaseCard>
</template>

<style scoped>
@reference "@/style.css";

.stage {
  @apply relative bg-black p-1 sm:p-2;
  width: 100%;
  min-height: 14rem;
  max-height: 70dvh;
}

@media (min-width: 64rem) {
  .stage {
    min-height: 22rem;
    max-height: min(72dvh, 52rem);
  }
}

@media print {
  .stage {
    background: white;
    max-height: none;
  }
}
</style>
