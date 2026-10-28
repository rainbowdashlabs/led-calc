// Hand-edited strip pieces that replace the generated ones (singleton).
// Edits belong to one strip geometry; when the geometry changes they are discarded.
import { readonly, ref } from 'vue'

const pieces = ref(null)
const signature = ref(null)

export function useManualEdits() {
  function commit(newPieces, geometrySignature) {
    pieces.value = newPieces
    signature.value = geometrySignature
  }
  function clear() {
    pieces.value = null
    signature.value = null
  }
  /** Edits for this geometry, or null; `stale` tells whether edits had to be dropped. */
  function validFor(geometrySignature) {
    if (pieces.value && signature.value !== geometrySignature) {
      clear()
      return { pieces: null, stale: true }
    }
    return { pieces: pieces.value, stale: false }
  }
  return { pieces: readonly(pieces), commit, clear, validFor }
}
