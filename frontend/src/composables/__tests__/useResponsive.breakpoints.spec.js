import { describe, expect, it } from 'vitest'
import { getDeviceType, RESPONSIVE_BREAKPOINTS } from '../useResponsive'

describe('responsive breakpoint baseline', () => {
  it('uses product breakpoints for mobile/tablet/desktop', () => {
    expect(RESPONSIVE_BREAKPOINTS.mobile).toBe(768)
    expect(RESPONSIVE_BREAKPOINTS.tablet).toBe(1200)
    expect(getDeviceType(390)).toBe('mobile')
    expect(getDeviceType(768)).toBe('tablet')
    expect(getDeviceType(1199)).toBe('tablet')
    expect(getDeviceType(1200)).toBe('desktop')
  })
})
