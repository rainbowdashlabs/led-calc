<script setup>
import { useI18n } from 'vue-i18n'
import IconButton from '@/components/button/IconButton.vue'
import RangeField from '@/components/input/RangeField.vue'

const MIN = 0.5
const MAX = 20
const STEP = 1.25

const zoom = defineModel({ type: Number, required: true })
const { t } = useI18n()
const clamp = (value) => Math.min(MAX, Math.max(MIN, value))
</script>

<template>
  <span class="inline-flex items-center gap-1 text-xs text-zinc-400">
    <IconButton :label="t('verkleinern')" @click="zoom = clamp(zoom / STEP)">−</IconButton>
    <RangeField v-model="zoom" :min="MIN" :max="8" :step="0.05" label="Zoom" class="!w-28" />
    <IconButton :label="t('vergroessern')" @click="zoom = clamp(zoom * STEP)">+</IconButton>
    <span class="w-10 text-right tabular-nums">{{ Math.round(zoom * 100) }} %</span>
  </span>
</template>
