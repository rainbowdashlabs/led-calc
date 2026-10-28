<script setup>
import { useI18n } from 'vue-i18n'
import BaseCard from '@/components/container/BaseCard.vue'
import ProgressBar from '@/components/display/ProgressBar.vue'
import { usePlanner } from '@/composables/usePlanner'
import { useProgressLabel } from '@/composables/useProgressLabel'

const { t } = useI18n()
const { progress } = usePlanner()
const label = useProgressLabel()
</script>

<template>
  <BaseCard class="!p-6 text-center text-zinc-400">
    <ProgressBar :fraction="progress.fraction" class="mx-auto mb-3 !h-1.5 w-64" />
    {{ label }}<br />
    <span class="text-xs">{{ t('beim_ersten_start_werden_ca') }}</span>
  </BaseCard>
</template>
