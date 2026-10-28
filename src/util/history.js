/**
 * Linear undo/redo history of immutable states (e.g. JSON strings).
 *
 * `record` adds a state unless it equals the current one and discards the redo branch;
 * `undo` / `redo` move along the history and return the state to restore (or null).
 */
export function createHistory({ limit = 50 } = {}) {
  const past = []
  const future = []
  let current = null

  return {
    /** Start over with `state` as the current state. */
    reset(state) {
      past.length = 0
      future.length = 0
      current = state
    },
    /** Remember `state` as the new current state; returns false if nothing changed. */
    record(state) {
      if (state === current) return false
      if (current !== null) past.push(current)
      if (past.length > limit) past.shift()
      future.length = 0
      current = state
      return true
    },
    undo() {
      if (!past.length) return null
      future.push(current)
      current = past.pop()
      return current
    },
    redo() {
      if (!future.length) return null
      past.push(current)
      current = future.pop()
      return current
    },
    get canUndo() {
      return past.length > 0
    },
    get canRedo() {
      return future.length > 0
    },
  }
}
