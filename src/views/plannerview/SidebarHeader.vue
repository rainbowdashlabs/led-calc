<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import FileButton from '@/components/button/FileButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import HintText from '@/components/display/HintText.vue'
import LanguageToggle from '@/components/input/LanguageToggle.vue'
import { useShare } from '@/composables/useShare'
import ShareDialog from './ShareDialog.vue'

const { t, locale } = useI18n()
const share = useShare()
const shareOpen = ref(false)
</script>

<template>
  <header class="space-y-2">
    <div class="flex items-start justify-between gap-2">
      <h1 class="text-xl font-bold tracking-tight">
        <span class="text-pink-400 drop-shadow-[0_0_8px_rgba(255,60,172,0.8)]">LED-Neon</span> {{ locale === 'de' ? 'Planer' : 'Planner' }}
      </h1>
      <LanguageToggle />
    </div>
    <HintText>{{ t('streifenlaenge_routing_hinter_der_platte') }}</HintText>
    <div class="flex gap-1">
      <SecondaryButton compact :title="t('layout_als_datei_speichern')" @click="share.saveFile">{{ t('speichern') }}</SecondaryButton>
      <SecondaryButton compact :title="t('code_link_teilen_oder_laden')" @click="shareOpen = true">Code</SecondaryButton>
      <FileButton accept=".json,application/json" :title="t('gespeicherte_datei_laden')" @select="share.loadFile">{{ t('laden') }}</FileButton>
    </div>
    <ShareDialog v-if="shareOpen" @close="shareOpen = false" />
  </header>
</template>
