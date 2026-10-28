<script setup>
import { useI18n } from 'vue-i18n'
import HighlightCard from '@/components/container/HighlightCard.vue'
import CharBadge from '@/components/display/CharBadge.vue'
import { usePlanner } from '@/composables/usePlanner'

const { t } = useI18n()
const { plan } = usePlanner()
</script>

<template>
  <HighlightCard v-if="plan.hidden.length">
    <h3 class="mb-2 font-semibold text-amber-300">{{ t('verdeckte_uebergaenge_hinter_der_platte') }}</h3>
    <ul class="grid gap-1.5 sm:grid-cols-2">
      <li v-for="entry in plan.hidden" :key="entry.glyph" class="flex items-center gap-2">
        <CharBadge>{{ entry.char }}</CharBadge>
        <span class="text-zinc-300">{{ entry.reason }} · {{ t('stueck_list', { list: entry.pieces.join(', ') }) }}</span>
      </li>
    </ul>
  </HighlightCard>
</template>
