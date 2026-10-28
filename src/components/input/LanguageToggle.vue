<script setup>
import { useI18n } from 'vue-i18n'
import SegmentedControl from './SegmentedControl.vue'

/** Switches the UI language; the choice is remembered (see util/i18n). */
const { locale, t } = useI18n()
const LANGUAGES = [{ value: 'de', label: 'DE' }, { value: 'en', label: 'EN' }]
</script>

<template>
  <SegmentedControl v-model="locale" :options="LANGUAGES" compact :title="t('sprache')" />
</template>
