<script setup>
import FrameCutSection from './settings/FrameCutSection.vue'
import LayingSection from './settings/LayingSection.vue'
import PlateSection from './settings/PlateSection.vue'
import PrintSection from './settings/PrintSection.vue'
import StripSection from './settings/StripSection.vue'
import TextSection from './settings/TextSection.vue'
import SidebarHeader from './SidebarHeader.vue'
</script>

<template>
  <aside class="space-y-5 border-r border-zinc-800 bg-zinc-950 p-4 pb-10 lg:h-screen lg:w-96 lg:shrink-0 lg:overflow-y-auto">
    <SidebarHeader />
    <TextSection />
    <LayingSection />
    <StripSection />
    <PlateSection />
    <FrameCutSection />
    <PrintSection />
  </aside>
</template>
