<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PrimaryButton from '@/components/button/PrimaryButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import HintText from '@/components/display/HintText.vue'
import FieldLabel from '@/components/input/FieldLabel.vue'
import ModalDialog from '@/components/layout/ModalDialog.vue'
import { useShare } from '@/composables/useShare'

const emit = defineEmits(['close'])
const { t } = useI18n()
const share = useShare()
const input = ref('')

onMounted(share.createCode)

async function load() {
  if (await share.loadCode(input.value)) emit('close')
}
</script>

<template>
  <ModalDialog :title="t('layout_code')" @close="emit('close')">
    <HintText>{{ t('der_code_enthaelt_alle_einstellungen') }}</HintText>
    <textarea readonly :value="share.code.value" rows="4" class="code-box" @focus="$event.target.select()" />
    <div class="flex gap-2">
      <PrimaryButton @click="share.copy(false)">{{ t('code_kopieren') }}</PrimaryButton>
      <SecondaryButton @click="share.copy(true)">{{ t('link_kopieren') }}</SecondaryButton>
    </div>
    <hr class="border-zinc-800" />
    <FieldLabel>{{ t('code_einfuegen_und_laden') }}</FieldLabel>
    <textarea v-model="input" rows="3" class="code-box" placeholder="NP1.…" />
    <div class="flex justify-end gap-2">
      <SecondaryButton @click="emit('close')">{{ t('schliessen') }}</SecondaryButton>
      <PrimaryButton :disabled="!input.trim()" @click="load">{{ t('laden') }}</PrimaryButton>
    </div>
  </ModalDialog>
</template>

<style scoped>
@reference "@/style.css";

.code-box {
  @apply w-full rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 font-mono text-xs text-zinc-100 focus:border-pink-500 focus:outline-none;
}
</style>
