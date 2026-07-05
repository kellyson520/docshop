import { beforeEach, describe, expect, it, vi } from 'vitest'
import { shouldReduceMotion } from '../useGsapMotion'

describe('useGsapMotion motion gate', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('data-motion-mode')
    localStorage.clear()
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn(() => ({
        matches: false,
        media: '(prefers-reduced-motion: reduce)',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
      }))
    })
  })

  it('disables GSAP when app motion mode is off', () => {
    document.documentElement.setAttribute('data-motion-mode', 'off')

    expect(shouldReduceMotion()).toBe(true)
  })

  it('disables GSAP when app motion mode is reduced', () => {
    document.documentElement.setAttribute('data-motion-mode', 'reduced')

    expect(shouldReduceMotion()).toBe(true)
  })

  it('uses system reduced-motion when app mode is system', () => {
    document.documentElement.setAttribute('data-motion-mode', 'system')
    window.matchMedia = vi.fn(() => ({
      matches: true,
      media: '(prefers-reduced-motion: reduce)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))

    expect(shouldReduceMotion()).toBe(true)
  })
})
