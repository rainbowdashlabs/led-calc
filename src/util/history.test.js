import { describe, expect, it } from 'vitest'
import { createHistory } from './history'

describe('createHistory', () => {
  it('undoes and redoes recorded states in order', () => {
    const h = createHistory()
    h.reset('a')
    h.record('b')
    h.record('c')
    expect(h.undo()).toBe('b')
    expect(h.undo()).toBe('a')
    expect(h.undo()).toBeNull()
    expect(h.redo()).toBe('b')
    expect(h.redo()).toBe('c')
    expect(h.redo()).toBeNull()
  })

  it('ignores a state equal to the current one', () => {
    const h = createHistory()
    h.reset('a')
    expect(h.record('a')).toBe(false)
    expect(h.canUndo).toBe(false)
  })

  it('drops the redo branch when something new is recorded', () => {
    const h = createHistory()
    h.reset('a')
    h.record('b')
    h.undo()
    h.record('x')
    expect(h.canRedo).toBe(false)
    expect(h.undo()).toBe('a')
  })

  it('keeps at most `limit` undo steps', () => {
    const h = createHistory({ limit: 2 })
    h.reset('0')
    for (const s of ['1', '2', '3', '4']) h.record(s)
    expect(h.undo()).toBe('3')
    expect(h.undo()).toBe('2')
    expect(h.undo()).toBeNull()
  })
})
