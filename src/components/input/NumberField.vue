<script setup>
import BaseInput from './BaseInput.vue'
import FieldLabel from './FieldLabel.vue'

/** Labelled number input. An empty field yields null (meaning "automatic"). */
const model = defineModel({ type: [Number, null] })
defineProps({
  label: { type: String, required: true },
  min: { type: Number, default: undefined },
  max: { type: Number, default: undefined },
  step: { type: Number, default: 1 },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
})

function update(event) {
  const raw = event.target.value
  model.value = raw === '' ? null : Number(raw)
}
</script>

<template>
  <div>
    <FieldLabel>{{ label }}</FieldLabel>
    <BaseInput type="number" :model-value="model ?? ''" :min="min" :max="max" :step="step" :placeholder="placeholder" :title="hint || undefined" @input="update" />
  </div>
</template>
