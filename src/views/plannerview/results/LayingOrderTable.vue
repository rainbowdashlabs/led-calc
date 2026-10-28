<script setup>
import { useI18n } from 'vue-i18n'
import TitledCard from '@/components/container/TitledCard.vue'
import { useFormat } from '@/composables/useFormat'
import { usePlanner } from '@/composables/usePlanner'
import { usePreviewState } from '@/composables/usePreviewState'

const ROLE_KEYS = { contour: 'kontur', line: 'linie', dot: 'punkt', frame: 'rahmen' }
const REASON_KEYS = {
  feed: 'einspeisung', same_glyph: 'im_selben_buchstaben', next_glyph: 'naechster_buchstabe',
  next_word: 'naechstes_wort', next_line: 'naechste_zeile', roll: 'rollenwechsel',
}

const { t } = useI18n()
const { fmtMm } = useFormat()
const { plan } = usePlanner()
const preview = usePreviewState()
</script>

<template>
  <TitledCard :title="t('verlegereihenfolge')">
    <div class="max-h-96 overflow-auto">
      <table class="w-full min-w-[30rem] text-sm">
        <thead class="sticky top-0 bg-zinc-900 text-xs text-zinc-500">
          <tr>
            <th class="px-3 py-1.5 text-left">#</th>
            <th class="text-left">{{ t('zeichen') }}</th>
            <th class="text-left">{{ t('art') }}</th>
            <th class="text-right">{{ t('laenge') }}</th>
            <th class="px-3 text-left">{{ t('davor_hinter_der_platte') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(piece, i) in plan.pieces"
            :key="piece.no"
            class="border-t border-zinc-800/70"
            :class="{ 'bg-pink-500/10': preview.hover === piece.no }"
            @mouseenter="preview.hover = piece.no"
            @mouseleave="preview.hover = null"
          >
            <td class="px-3 py-1.5 font-semibold">{{ piece.no }}</td>
            <td>{{ piece.char }}</td>
            <td :class="piece.role === 'dot' ? 'text-amber-300' : 'text-zinc-400'">
              {{ t(ROLE_KEYS[piece.role]) }}{{ piece.inner ? t('innen') : '' }}
              <span v-if="piece.violations.length" class="ml-1 text-red-400" :title="t('n_enge_stelle_n', { n: piece.violations.length })">●</span>
            </td>
            <td class="text-right">{{ fmtMm(piece.length) }}</td>
            <td class="px-3 text-xs" :class="plan.links[i].reason === 'same_glyph' ? 'text-amber-300' : 'text-zinc-400'">
              {{ plan.links[i].kind === 'strip' ? t('streifen') : t('kabel') }} {{ fmtMm(plan.links[i].length) }} · {{ t(REASON_KEYS[plan.links[i].reason]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </TitledCard>
</template>
