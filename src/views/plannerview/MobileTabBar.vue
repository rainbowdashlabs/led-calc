<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '@/components/display/AppIcon.vue'
import { useMobileTabs } from '@/composables/useMobileTabs'

/** Bottom navigation on phones and tablets; switches between the three areas. */
const { t } = useI18n()
const { tab, TABS } = useMobileTabs()

const items = computed(() => [
  { value: TABS.SETTINGS, icon: 'sliders', label: t('tab_einstellungen') },
  { value: TABS.PREVIEW, icon: 'eye', label: t('tab_vorschau') },
  { value: TABS.RESULTS, icon: 'list', label: t('tab_ergebnis') },
])
</script>

<template>
  <nav class="tab-bar" :aria-label="t('tab_navigation')">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="tab"
      :class="tab === item.value ? 'text-pink-300' : 'text-zinc-400'"
      :aria-current="tab === item.value ? 'page' : undefined"
      @click="tab = item.value"
    >
      <AppIcon :name="item.icon" :size="20" />
      <span class="text-[11px]">{{ item.label }}</span>
      <i v-if="tab === item.value" class="absolute inset-x-6 top-0 h-0.5 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(255,60,172,0.9)]" />
    </button>
  </nav>
</template>

<style scoped>
@reference "@/style.css";

.tab-bar {
  @apply fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur;
  padding-bottom: env(safe-area-inset-bottom);
}

.tab {
  @apply relative flex flex-col items-center gap-0.5 py-2 transition;
}
</style>
