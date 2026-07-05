
import { describe, it, expect, vi, beforeEach } from 'vitest'

function makeFetch(config) {
  return vi.fn(async (url) => {
    expect(url).toBe('/api/v1/tracking/config')
    return {
      ok: true,
      async json() {
        return { code: 0, data: config }
      }
    }
  })
}

function makeDeps(config, cookie = 'device_id=visitor-1; session_id=session-1') {
  const beacons = []
  const sendBeacon = vi.fn((url, blob) => {
    beacons.push({ url, blob })
    return true
  })
  const localStore = new Map()
  const sessionStore = new Map()
  return {
    beacons,
    fetchImpl: makeFetch(config),
    navigatorObj: {
      sendBeacon,
      language: 'zh-CN',
      hardwareConcurrency: 8,
      maxTouchPoints: 1,
    },
    windowObj: {
      location: { pathname: '/admin/tracking', search: '' },
      devicePixelRatio: 2,
      screen: { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24 },
      matchMedia: vi.fn(() => ({ matches: false })),
    },
    documentObj: { cookie },
    localStorageObj: {
      getItem: vi.fn((key) => (localStore.has(key) ? localStore.get(key) : null)),
      setItem: vi.fn((key, value) => localStore.set(key, String(value))),
    },
    sessionStorageObj: {
      getItem: vi.fn((key) => (sessionStore.has(key) ? sessionStore.get(key) : null)),
      setItem: vi.fn((key, value) => sessionStore.set(key, String(value))),
    },
  }
}

async function beaconJson(call) {
  return JSON.parse(call.blob)
}

async function loadTrackingClient() {
  return import('../trackingClient.js')
}

describe('trackingClient', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.restoreAllMocks()
  })

  it('does not send a beacon when tracking is disabled', async () => {
    const { initTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: false })

    await initTracking(deps)

    expect(deps.navigatorObj.sendBeacon).not.toHaveBeenCalled()
  })

  it('does not ask for geolocation when location tracking is disabled', async () => {
    const { initTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })
    deps.navigatorObj.geolocation = { getCurrentPosition: vi.fn() }

    await initTracking(deps)

    expect(deps.navigatorObj.geolocation.getCurrentPosition).not.toHaveBeenCalled()
    expect(deps.beacons).toHaveLength(1)
    expect(deps.beacons[0].url).toBe('/api/v1/tracking/ping')
    const payload = await beaconJson(deps.beacons[0])
    expect(payload.device_id).toBe('visitor-1')
    expect(payload.session_id).toBe('session-1')
    expect(payload.page_path).toBeUndefined()
    expect(payload.screen_resolution).toBe('1920x1080')
    expect(payload.client_language).toBe('zh-CN')
  })

  it('sends init tracking without page_path and keeps page_path only for SPA page views', async () => {
    const { initTracking, sendPageViewTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })

    await initTracking(deps)
    const initPayload = await beaconJson(deps.beacons[0])
    expect(initPayload.page_path).toBeUndefined()

    sendPageViewTracking(deps)
    const pageViewPayload = await beaconJson(deps.beacons[1])
    expect(pageViewPayload.page_path).toBe('/admin/tracking')
  })

  it('includes high-entropy UA client hints model for Android Chrome and Edge', async () => {
    const { initTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })
    deps.navigatorObj.userAgentData = {
      getHighEntropyValues: vi.fn(async (hints) => {
        expect(hints).toContain('model')
        return {
          model: 'V2243A',
          platform: 'Android',
          platformVersion: '16.0.0',
          architecture: 'arm',
          bitness: '64',
        }
      }),
    }

    await initTracking(deps)

    expect(deps.navigatorObj.userAgentData.getHighEntropyValues).toHaveBeenCalled()
    const payload = await beaconJson(deps.beacons[0])
    expect(payload.device_model).toBe('V2243A')
    expect(payload.platform).toBe('Android')
    expect(payload.platform_version).toBe('16.0.0')
    expect(payload.cpu_architecture).toBe('arm')
    expect(payload.cpu_bitness).toBe('64')
  })

  it('includes browser geolocation when enabled and permission succeeds', async () => {
    const { initTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: true })
    deps.navigatorObj.geolocation = {
      getCurrentPosition: vi.fn((success) => success({ coords: { latitude: 39.9042, longitude: 116.4074, accuracy: 8.5 } }))
    }

    await initTracking(deps)

    expect(deps.navigatorObj.geolocation.getCurrentPosition).toHaveBeenCalled()
    const payload = await beaconJson(deps.beacons[0])
    expect(payload.geo_latitude).toBe(39.9042)
    expect(payload.geo_longitude).toBe(116.4074)
    expect(payload.geo_accuracy).toBe(8.5)
  })

  it('queues the first SPA page view until tracking init finishes', async () => {
    const { initTracking, sendPageViewTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })

    let resolveConfig
    deps.fetchImpl = vi.fn(async () => {
      await new Promise((resolve) => {
        resolveConfig = resolve
      })
      return {
        ok: true,
        async json() {
          return {
            code: 0,
            data: {
              enable_tracking: true,
              enable_device_tracking: true,
              enable_location_tracking: false,
            },
          }
        },
      }
    })

    const initPromise = initTracking(deps)
    const earlySend = sendPageViewTracking(deps)

    expect(earlySend).toBe(false)
    expect(deps.navigatorObj.sendBeacon).not.toHaveBeenCalled()

    resolveConfig()
    await initPromise

    expect(deps.beacons).toHaveLength(2)
    const initPayload = await beaconJson(deps.beacons[0])
    const pageViewPayload = await beaconJson(deps.beacons[1])
    expect(initPayload.page_path).toBeUndefined()
    expect(pageViewPayload.page_path).toBe('/admin/tracking')
  })

  it('sends a page-view beacon for later SPA route changes', async () => {
    const { initTracking, sendPageViewTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })

    await initTracking(deps)
    deps.beacons.length = 0
    deps.windowObj.location.pathname = '/admin/dashboard'
    const first = sendPageViewTracking(deps)
    deps.windowObj.location.pathname = '/admin/tracking'
    const second = sendPageViewTracking(deps)

    expect(first).toBe(true)
    expect(second).toBe(true)
    expect(deps.beacons).toHaveLength(2)
    const firstPayload = await beaconJson(deps.beacons[0])
    expect(firstPayload.screen_resolution).toBe('1920x1080')
    expect(firstPayload.client_language).toBe('zh-CN')
    expect(firstPayload.client_timezone).toBeTruthy()
  })

  it('persists identifiers from tracking config and reuses them for page views', async () => {
    const { initTracking, sendPageViewTracking } = await loadTrackingClient()
    const deps = makeDeps({
      enable_tracking: true,
      enable_device_tracking: true,
      enable_location_tracking: false,
      device_id: 'visitor-9',
      session_id: 'session-9',
    }, '')

    await initTracking(deps)
    expect(deps.localStorageObj.setItem).toHaveBeenCalledWith('tracking_device_id', 'visitor-9')
    expect(deps.sessionStorageObj.setItem).toHaveBeenCalledWith('tracking_session_id', 'session-9')
    deps.beacons.length = 0
    sendPageViewTracking(deps)

    expect(deps.beacons).toHaveLength(1)
    const payload = await beaconJson(deps.beacons[0])
    expect(payload.device_id).toBe('visitor-9')
    expect(payload.session_id).toBe('session-9')
    expect(payload.page_path).toBe('/admin/tracking')
  })

  it('does not send a page-view beacon when config and cookies both lack identifiers', async () => {
    const { initTracking, sendPageViewTracking } = await loadTrackingClient()
    const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false }, '')

    await initTracking(deps)
    deps.beacons.length = 0
    const sent = sendPageViewTracking(deps)

    expect(sent).toBe(false)
    expect(deps.beacons).toHaveLength(0)
  })
})
