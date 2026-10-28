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
document.documentElement.lang = locale.value
watch(locale, (v) => {
  document.documentElement.lang = v
  try { localStorage.setItem(STORAGE_KEY, v) } catch { /* ignore */ }
})
