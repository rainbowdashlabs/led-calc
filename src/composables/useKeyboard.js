// Global keyboard shortcuts, active while `enabled()` is true. Bindings are keyed by a
// combination such as 'mod+z', 'mod+shift+z' or 'delete' ('mod' = Ctrl or ⌘). Typing
// into form fields is never intercepted, so their native undo keeps working.
import { onBeforeUnmount, onMounted } from 'vue'

const FORM_FIELDS = ['INPUT', 'TEXTAREA', 'SELECT']

/** 'mod+shift+z' style name of a keyboard event. */
export function comboOf(event) {
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key.toLowerCase()
  return [event.ctrlKey || event.metaKey ? 'mod' : '', event.shiftKey && key.length === 1 ? 'shift' : '', key]
    .filter(Boolean)
    .join('+')
}

export function useKeyboard(bindings, enabled = () => true) {
  function onKey(event) {
    if (!enabled() || FORM_FIELDS.includes(document.activeElement?.tagName)) return
    const action = bindings[comboOf(event)]
    if (action) {
      event.preventDefault()
      action()
    }
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
}
