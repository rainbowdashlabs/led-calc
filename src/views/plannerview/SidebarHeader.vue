<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import FileButton from '@/components/button/FileButton.vue'
import SecondaryButton from '@/components/button/SecondaryButton.vue'
import HintText from '@/components/display/HintText.vue'
import LanguageToggle from '@/components/input/LanguageToggle.vue'
import { useShare } from '@/composables/useShare'
import AppTitle from './AppTitle.vue'
import ShareDialog from './ShareDialog.vue'

const { t } = useI18n()
const share = useShare()
const shareOpen = ref(false)
</script>

<template>
  <header class="space-y-2">
    <!-- on small screens title and language live in the MobileHeader -->
    <div class="hidden items-start justify-between gap-2 lg:flex">
      <AppTitle class="text-xl" />
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
