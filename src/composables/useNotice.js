// Short-lived notice shown below the preview (singleton).
import { readonly, ref } from 'vue'

const notice = ref('')
let timer = null

export function useNotice() {
  function flash(message) {
    notice.value = message
    clearTimeout(timer)
    timer = setTimeout(() => (notice.value = ''), 5000)
  }
  return { notice: readonly(notice), flash }
}
