import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ROUTE_PROGRESS_ATTR,
  finishRouteProgress,
  resetRouteProgress,
  startRouteProgress
} from '../routeProgress'

describe('route progress utilities', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetRouteProgress()
  })

  afterEach(() => {
    resetRouteProgress()
    vi.useRealTimers()
  })

  it('marks navigation as loading and then settles back to idle', () => {
    startRouteProgress()
    expect(document.documentElement.getAttribute(ROUTE_PROGRESS_ATTR)).toBe('loading')

    finishRouteProgress()
    expect(document.documentElement.getAttribute(ROUTE_PROGRESS_ATTR)).toBe('complete')

    vi.advanceTimersByTime(220)
    expect(document.documentElement.getAttribute(ROUTE_PROGRESS_ATTR)).toBe('idle')
  })
})
