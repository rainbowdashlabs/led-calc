<script setup>
import { useI18n } from 'vue-i18n'
import TitledCard from '@/components/container/TitledCard.vue'
import { useFormat } from '@/composables/useFormat'
import { usePlanner } from '@/composables/usePlanner'

const { t } = useI18n()
const { fmtMm } = useFormat()
const { plan } = usePlanner()

/** "3–9" for long consecutive runs, "1, 4" otherwise. */
const pieceList = (nums) => (nums.length > 4 ? `${nums[0]}–${nums[nums.length - 1]}` : nums.join(', '))
</script>

<template>
  <TitledCard :title="t('zuschnittliste')">
    <table class="w-full text-sm">
      <thead class="text-xs text-zinc-500">
        <tr>
          <th class="px-3 py-1.5 text-left">{{ t('zuschnitt') }}</th>
          <th class="text-left">{{ t('stuecke') }}</th>
          <th class="text-right">{{ t('vorne') }}</th>
          <th class="text-right">{{ t('hinten') }}</th>
          <th class="px-3 text-right">{{ t('abschneiden') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="group in plan.groups" :key="group.no" class="border-t border-zinc-800/70">
          <td class="px-3 py-1.5 font-semibold">Z{{ group.no }}</td>
          <td class="text-zinc-400">
            {{ pieceList(group.pieces) }}
            <div v-for="note in group.notes" :key="note" class="text-xs text-amber-300">{{ note }}</div>
          </td>
          <td class="text-right">{{ fmtMm(group.front) }}</td>
          <td class="text-right">{{ fmtMm(group.back) }}</td>
          <td class="px-3 text-right font-semibold text-pink-300">{{ fmtMm(group.cut) }}</td>
        </tr>
      </tbody>
    </table>
  </TitledCard>
</template>
