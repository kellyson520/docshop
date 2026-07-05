import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resolveRouteScrollPosition } from '../routeScroll'

describe('route scroll behavior', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('data-motion-mode')
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

  it('restores browser saved position for back/forward navigation', () => {
    const saved = { left: 12, top: 240 }

    expect(resolveRouteScrollPosition({}, {}, saved)).toBe(saved)
  })

  it('scrolls to hash targets smoothly by default', () => {
    expect(resolveRouteScrollPosition({ hash: '#files' }, {}, null)).toEqual({
      el: '#files',
      behavior: 'smooth'
    })
  })

  it('uses instant scrolling when motion is reduced', () => {
    document.documentElement.setAttribute('data-motion-mode', 'reduced')

    expect(resolveRouteScrollPosition({ hash: '#files' }, {}, null)).toEqual({
      el: '#files',
      behavior: 'auto'
    })
  })

  it('resets normal page navigation to top', () => {
    expect(resolveRouteScrollPosition({ path: '/admin/settings' }, { path: '/admin/projects' }, null)).toEqual({
      left: 0,
      top: 0,
      behavior: 'smooth'
    })
  })
})
