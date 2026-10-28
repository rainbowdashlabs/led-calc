<script setup>
import CutListTable from './CutListTable.vue'
import CutOutInfo from './CutOutInfo.vue'
import HiddenTransitions from './HiddenTransitions.vue'
import LayingOrderTable from './LayingOrderTable.vue'
import PlanMessages from './PlanMessages.vue'
import SummaryCards from './SummaryCards.vue'
</script>

<template>
  <div class="space-y-4">
    <PlanMessages />
    <SummaryCards />
    <HiddenTransitions />
    <CutOutInfo />
    <div class="grid gap-4 xl:grid-cols-2">
      <CutListTable />
      <LayingOrderTable />
    </div>
  </div>
</template>
