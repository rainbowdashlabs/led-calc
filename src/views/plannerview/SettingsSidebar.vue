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
  <aside class="mx-auto max-w-2xl space-y-5 bg-zinc-950 p-4 pb-10 lg:h-dvh lg:w-96 lg:max-w-none lg:shrink-0 lg:overflow-y-auto lg:border-r lg:border-zinc-800 xl:w-[26rem] 2xl:w-[28rem]">
    <SidebarHeader />
    <TextSection />
    <LayingSection />
    <StripSection />
    <PlateSection />
    <FrameCutSection />
    <PrintSection />
  </aside>
</template>
