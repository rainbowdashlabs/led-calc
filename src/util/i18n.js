// Localisation with vue-i18n (German / English). The initial language follows the
// browser; the user can toggle it and the choice is remembered.
import { watch } from 'vue'
import { createI18n } from 'vue-i18n'
import de from '@/locales/de.json'
import en from '@/locales/en.json'

const STORAGE_KEY = 'led-neon-planer:lang'

function detect() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'de' || saved === 'en') return saved
  } catch { /* storage unavailable */ }
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language || 'en']
  return langs.some((l) => l.toLowerCase().startsWith('de')) ? 'de' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: detect(),
  fallbackLocale: 'de',
  messages: { de, en },
  missingWarn: false,
  fallbackWarn: false,
})

const locale = i18n.global.locale

/** Keep <html lang> and the page title in the chosen language. */
function applyLocale(value) {
  document.documentElement.lang = value
  document.title = i18n.global.t('seitentitel')
}

applyLocale(locale.value)
watch(locale, (value) => {
  applyLocale(value)
  try { localStorage.setItem(STORAGE_KEY, value) } catch { /* ignore */ }
})
