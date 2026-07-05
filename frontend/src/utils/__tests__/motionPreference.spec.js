import { beforeEach, describe, expect, it } from 'vitest'
import {
  MOTION_STORAGE_KEY,
  applyMotionPreference,
  bindMotionPreferenceSync,
  getStoredMotionMode,
  initMotionPreference,
  normalizeMotionMode
} from '../motionPreference'

describe('motion preference utilities', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-motion-mode')
  })

  it('normalizes unknown modes to system', () => {
    expect(normalizeMotionMode('off')).toBe('off')
    expect(normalizeMotionMode('reduced')).toBe('reduced')
    expect(normalizeMotionMode('invalid')).toBe('system')
    expect(normalizeMotionMode()).toBe('system')
  })

  it('applies and persists the selected motion mode', () => {
    const mode = applyMotionPreference('off')

    expect(mode).toBe('off')
    expect(localStorage.getItem(MOTION_STORAGE_KEY)).toBe('off')
    expect(document.documentElement.getAttribute('data-motion-mode')).toBe('off')
  })

  it('initializes from localStorage and falls back to system', () => {
    localStorage.setItem(MOTION_STORAGE_KEY, 'reduced')

    expect(getStoredMotionMode()).toBe('reduced')
    expect(initMotionPreference()).toBe('reduced')
    expect(document.documentElement.getAttribute('data-motion-mode')).toBe('reduced')

    localStorage.setItem(MOTION_STORAGE_KEY, 'bad-value')
    expect(initMotionPreference()).toBe('system')
    expect(document.documentElement.getAttribute('data-motion-mode')).toBe('system')
  })

  it('syncs motion mode changes from other tabs through storage events', () => {
    const stopSync = bindMotionPreferenceSync()

    window.dispatchEvent(new StorageEvent('storage', {
      key: MOTION_STORAGE_KEY,
      newValue: 'off'
    }))

    expect(document.documentElement.getAttribute('data-motion-mode')).toBe('off')

    stopSync()
    window.dispatchEvent(new StorageEvent('storage', {
      key: MOTION_STORAGE_KEY,
      newValue: 'reduced'
    }))

    expect(document.documentElement.getAttribute('data-motion-mode')).toBe('off')
  })
})
