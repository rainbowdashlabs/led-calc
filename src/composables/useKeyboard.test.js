import { describe, expect, it } from 'vitest'
import { comboOf } from './useKeyboard'

const ev = (key, mods = {}) => ({ key, ctrlKey: false, metaKey: false, shiftKey: false, ...mods })

describe('comboOf', () => {
  it('names plain keys in lower case', () => {
    expect(comboOf(ev('Delete'))).toBe('delete')
    expect(comboOf(ev('Escape'))).toBe('escape')
  })
  it('treats Ctrl and ⌘ alike', () => {
    expect(comboOf(ev('z', { ctrlKey: true }))).toBe('mod+z')
    expect(comboOf(ev('z', { metaKey: true }))).toBe('mod+z')
  })
  it('includes shift for letters (Z with shift arrives as upper case)', () => {
    expect(comboOf(ev('Z', { ctrlKey: true, shiftKey: true }))).toBe('mod+shift+z')
  })
})
