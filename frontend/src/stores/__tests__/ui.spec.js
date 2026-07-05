import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUiStore } from '../ui.js'

function mockSystemTheme(matches = false) {
  const listeners = new Set()
  const mediaQuery = {
    matches,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addListener: vi.fn((listener) => listeners.add(listener)),
    removeListener: vi.fn((listener) => listeners.delete(listener)),
    addEventListener: vi.fn((event, listener) => {
      if (event === 'change') listeners.add(listener)
    }),
    removeEventListener: vi.fn((event, listener) => {
      if (event === 'change') listeners.delete(listener)
    }),
    dispatchEvent: vi.fn()
  }

  window.matchMedia = vi.fn().mockImplementation(() => mediaQuery)

  return {
    mediaQuery,
    emitChange(nextMatches) {
      mediaQuery.matches = nextMatches
      listeners.forEach((listener) => listener({ matches: nextMatches }))
      if (typeof mediaQuery.onchange === 'function') {
        mediaQuery.onchange({ matches: nextMatches })
      }
    }
  }
}

describe('ui store theme behavior', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('uses the system dark theme on init when there is no saved preference', () => {
    mockSystemTheme(true)

    const store = useUiStore()
    store.initTheme()

    expect(store.theme).toBe('dark')
    expect(store.isDark).toBe(true)
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('keeps following system theme changes until the user explicitly toggles the theme', () => {
    const { emitChange } = mockSystemTheme(false)

    const store = useUiStore()
    store.initTheme()
    expect(store.theme).toBe('light')

    emitChange(true)

    expect(store.theme).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    store.toggleTheme()
    expect(store.theme).toBe('light')

    emitChange(true)

    expect(store.theme).toBe('light')
    expect(localStorage.getItem('ui_theme')).toBe('light')
  })
})
