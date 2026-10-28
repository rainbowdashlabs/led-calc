// Save and load a layout: JSON file (incl. an uploaded font) or a compact share code / link.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { decodeCode, downloadJson, encodeCode, FORMAT, VERSION } from '@/util/share'
import { useEditor } from './useEditor'
import { useFonts } from './useFonts'
import { useManualEdits } from './useManualEdits'
import { useNotice } from './useNotice'
import { usePlanner } from './usePlanner'
import { useSettings } from './useSettings'

export function useShare() {
  const { t } = useI18n()
  const { settings, reset } = useSettings()
  const { customFont, setCustomFont } = useFonts()
  const manual = useManualEdits()
  const { signature, schedule } = usePlanner()
  const editor = useEditor()
  const { flash } = useNotice()
  const code = ref('')

  const fileName = () => `led-neon-${settings.text.trim().replace(/\s+/g, '-').replace(/[^\p{L}\p{N}-]/gu, '').slice(0, 30) || 'plan'}`

  function snapshot(includeFont) {
    const data = { format: FORMAT, version: VERSION, settings: { ...settings }, manual: manual.pieces.value }
    if (includeFont && settings.fontId === 'custom' && customFont.value) {
      let bin = ''
      const bytes = customFont.value.bytes
      for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
      data.customFont = { name: customFont.value.name, data: btoa(bin) }
    }
    return data
  }

  async function apply(data) {
    if (data?.format !== FORMAT) throw new Error(t('keine_datei_des_led_neon'))
    if (data.customFont) setCustomFont(data.customFont.name, Uint8Array.from(atob(data.customFont.data), (c) => c.charCodeAt(0)))
    reset(data.settings)
    if (settings.fontId === 'custom' && !customFont.value) {
      settings.fontId = 'pacifico'
      flash(t('die_gespeicherte_eigene_schrift_ist'))
    }
    editor.finish()
    // the signature reflects the restored settings once Vue has updated the computed values
    await Promise.resolve()
    if (data.manual) manual.commit(data.manual, signature.value)
    else manual.clear()
    schedule()
  }

  const saveFile = () => downloadJson(snapshot(true), `${fileName()}.neonplan.json`)

  async function loadFile(file) {
    try {
      await apply(JSON.parse(await file.text()))
      flash(t('layout_geladen'))
    } catch (e) {
      flash(t('datei_konnte_nicht_gelesen_werden') + (e.message || e))
    }
  }

  async function createCode() {
    code.value = await encodeCode(snapshot(false))
  }

  async function copy(asLink) {
    const text = asLink ? `${location.origin}${location.pathname}#p=${code.value}` : code.value
    try {
      await navigator.clipboard.writeText(text)
      flash(asLink ? t('link_kopiert') : t('code_kopiert'))
    } catch {
      flash(t('kopieren_nicht_moeglich_bitte_manuell'))
    }
  }

  /** Load from a code or a link (#p=...); returns true on success. */
  async function loadCode(text, fromLink = false) {
    try {
      await apply(await decodeCode(text))
      flash(fromLink ? t('layout_aus_link_geladen') : t('layout_geladen'))
      return true
    } catch (e) {
      flash(fromLink ? t('link_enthaelt_kein_gueltiges_layout') : t('code_konnte_nicht_gelesen_werden') + (e.message || e))
      return false
    }
  }

  return { code, fileName, saveFile, loadFile, createCode, copy, loadCode }
}
