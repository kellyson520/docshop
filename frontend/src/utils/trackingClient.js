
const CONFIG_URL = '/api/v1/tracking/config'
const PING_URL = '/api/v1/tracking/ping'
const TRACKING_DEVICE_STORAGE_KEY = 'tracking_device_id'
const TRACKING_SESSION_STORAGE_KEY = 'tracking_session_id'

let trackingEnabled = false
let trackingReady = false
let pendingPageView = null

function unwrapConfig(body) {
  if (body && typeof body === 'object' && body.code === 0 && body.data) return body.data
  return body
}

function getCookie(name, documentObj = document) {
  const cookie = documentObj?.cookie || ''
  const match = cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function getCurrentPagePath(windowObj = window) {
  const pathname = windowObj?.location?.pathname || ''
  const search = windowObj?.location?.search || ''
  const pagePath = `${pathname}${search}`.trim()
  return pagePath || '/'
}

function getStorageValue(storageObj, key) {
  try {
    return storageObj?.getItem?.(key) || null
  } catch {
    return null
  }
}

function setStorageValue(storageObj, key, value) {
  if (!value) return
  try {
    storageObj?.setItem?.(key, String(value))
  } catch {}
}

function buildTrackingIdentifiers({
  documentObj = document,
  localStorageObj = globalThis?.localStorage,
  sessionStorageObj = globalThis?.sessionStorage,
} = {}) {
  const deviceId = getStorageValue(localStorageObj, TRACKING_DEVICE_STORAGE_KEY) || getCookie('device_id', documentObj)
  const sessionId = getStorageValue(sessionStorageObj, TRACKING_SESSION_STORAGE_KEY) || getCookie('session_id', documentObj)
  return Object.fromEntries(
    Object.entries({
      device_id: deviceId || undefined,
      session_id: sessionId || undefined,
    }).filter(([, value]) => value !== undefined)
  )
}

function persistTrackingIdentifiers(config, {
  localStorageObj = globalThis?.localStorage,
  sessionStorageObj = globalThis?.sessionStorage,
} = {}) {
  setStorageValue(localStorageObj, TRACKING_DEVICE_STORAGE_KEY, config?.device_id)
  setStorageValue(sessionStorageObj, TRACKING_SESSION_STORAGE_KEY, config?.session_id)
}

function hasTrackingIdentifiers(identifiers) {
  return Boolean(identifiers?.device_id || identifiers?.session_id)
}

async function getTrackingConfig(fetchImpl = fetch) {
  try {
    const response = await fetchImpl(CONFIG_URL)
    if (response && response.ok === false) return null
    return unwrapConfig(await response.json())
  } catch {
    return null
  }
}

function safeMatch(windowObj, query) {
  try {
    return Boolean(windowObj?.matchMedia?.(query)?.matches)
  } catch {
    return undefined
  }
}

export function collectSyncDeviceData({ navigatorObj = navigator, windowObj = window } = {}) {
  const payload = {}
  const screen = windowObj?.screen
  if (screen) {
    if (screen.width && screen.height) payload.screen_resolution = `${screen.width}x${screen.height}`
    if (screen.availWidth && screen.availHeight) payload.screen_avail = `${screen.availWidth}x${screen.availHeight}`
    if (screen.colorDepth !== undefined) payload.screen_color_depth = screen.colorDepth
    try {
      if (screen.orientation?.type) payload.screen_orientation = screen.orientation.type
    } catch {}
  }
  if (windowObj?.devicePixelRatio !== undefined) payload.screen_pixel_ratio = windowObj.devicePixelRatio
  if (navigatorObj?.platform) payload.platform = navigatorObj.platform
  if (navigatorObj?.hardwareConcurrency !== undefined) payload.hardware_concurrency = navigatorObj.hardwareConcurrency
  if (navigatorObj?.deviceMemory !== undefined) payload.device_memory = navigatorObj.deviceMemory
  if (navigatorObj?.maxTouchPoints !== undefined) payload.max_touch_points = navigatorObj.maxTouchPoints
  payload.touch_support = Boolean(windowObj && 'ontouchstart' in windowObj)
  payload.pointer_coarse = safeMatch(windowObj, '(pointer: coarse)')
  payload.pointer_fine = safeMatch(windowObj, '(pointer: fine)')
  payload.hover_hover = safeMatch(windowObj, '(hover: hover)')
  payload.any_pointer_coarse = safeMatch(windowObj, '(any-pointer: coarse)')
  payload.any_pointer_fine = safeMatch(windowObj, '(any-pointer: fine)')
  if (navigatorObj?.connection) {
    payload.network_type = navigatorObj.connection.effectiveType
    payload.network_downlink = navigatorObj.connection.downlink
    payload.network_rtt = navigatorObj.connection.rtt
    payload.network_save_data = Boolean(navigatorObj.connection.saveData)
  }
  if (navigatorObj?.language) payload.client_language = navigatorObj.language
  try {
    payload.client_timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {}
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== undefined && value !== null))
}

async function collectHighEntropyDeviceData(navigatorObj = navigator) {
  const getHighEntropyValues = navigatorObj?.userAgentData?.getHighEntropyValues
  if (typeof getHighEntropyValues !== 'function') return {}

  try {
    const values = await getHighEntropyValues.call(navigatorObj.userAgentData, [
      'model',
      'platform',
      'platformVersion',
      'architecture',
      'bitness',
    ])
    const payload = {}
    if (values?.model) payload.device_model = values.model
    if (values?.platform) payload.platform = values.platform
    if (values?.platformVersion) payload.platform_version = values.platformVersion
    if (values?.architecture) payload.cpu_architecture = values.architecture
    if (values?.bitness) payload.cpu_bitness = values.bitness
    return payload
  } catch {
    return {}
  }
}

function collectLocation(navigatorObj = navigator) {
  return new Promise((resolve) => {
    if (!navigatorObj?.geolocation?.getCurrentPosition) return resolve({})
    navigatorObj.geolocation.getCurrentPosition(
      (position) => resolve({
        geo_latitude: position.coords.latitude,
        geo_longitude: position.coords.longitude,
        geo_accuracy: position.coords.accuracy,
      }),
      () => resolve({}),
      { timeout: 5000, enableHighAccuracy: true, maximumAge: 300000 }
    )
  })
}

function sendTrackingBeacon(payload, { navigatorObj = navigator, fetchImpl = fetch } = {}) {
  const body = JSON.stringify(payload)
  if (navigatorObj?.sendBeacon?.(PING_URL, body)) return true
  fetchImpl(PING_URL, {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/json' },
    keepalive: true,
    credentials: 'include',
  }).catch(() => {})
  return false
}

function queuePendingPageView({
  fetchImpl = fetch,
  navigatorObj = navigator,
  windowObj = window,
  documentObj = document,
  localStorageObj = globalThis?.localStorage,
  sessionStorageObj = globalThis?.sessionStorage,
} = {}) {
  pendingPageView = {
    fetchImpl,
    navigatorObj,
    documentObj,
    localStorageObj,
    sessionStorageObj,
    payload: {
      page_path: getCurrentPagePath(windowObj),
      ...collectSyncDeviceData({ navigatorObj, windowObj }),
    },
  }
  return false
}

function flushPendingPageView() {
  if (!trackingEnabled || !trackingReady || !pendingPageView) return false

  const { fetchImpl, navigatorObj, documentObj, localStorageObj, sessionStorageObj, payload } = pendingPageView
  pendingPageView = null
  const identifiers = buildTrackingIdentifiers({ documentObj, localStorageObj, sessionStorageObj })
  if (!hasTrackingIdentifiers(identifiers)) return false
  return sendTrackingBeacon(
    {
      ...identifiers,
      ...payload,
    },
    { navigatorObj, fetchImpl }
  )
}

export function sendPageViewTracking({
  fetchImpl = fetch,
  navigatorObj = navigator,
  windowObj = window,
  documentObj = document,
  localStorageObj = globalThis?.localStorage,
  sessionStorageObj = globalThis?.sessionStorage,
} = {}) {
  if (!trackingEnabled || !trackingReady) {
    return queuePendingPageView({ fetchImpl, navigatorObj, windowObj, documentObj, localStorageObj, sessionStorageObj })
  }

  const identifiers = buildTrackingIdentifiers({ documentObj, localStorageObj, sessionStorageObj })
  if (!hasTrackingIdentifiers(identifiers)) return false

  const payload = {
    ...identifiers,
    page_path: getCurrentPagePath(windowObj),
    ...collectSyncDeviceData({ navigatorObj, windowObj }),
  }

  return sendTrackingBeacon(payload, { navigatorObj, fetchImpl })
}

export async function initTracking({
  fetchImpl = fetch,
  navigatorObj = navigator,
  windowObj = window,
  documentObj = document,
  localStorageObj = globalThis?.localStorage,
  sessionStorageObj = globalThis?.sessionStorage,
} = {}) {
  trackingEnabled = false
  trackingReady = false

  const config = await getTrackingConfig(fetchImpl)
  if (!config?.enable_tracking) {
    pendingPageView = null
    return false
  }

  trackingEnabled = true
  persistTrackingIdentifiers(config, { localStorageObj, sessionStorageObj })
  const identifiers = buildTrackingIdentifiers({ documentObj, localStorageObj, sessionStorageObj })
  if (!hasTrackingIdentifiers(identifiers)) {
    trackingReady = true
    pendingPageView = null
    return false
  }

  const payload = {
    ...identifiers,
  }

  if (config.enable_device_tracking !== false) {
    Object.assign(payload, collectSyncDeviceData({ navigatorObj, windowObj }))
    Object.assign(payload, await collectHighEntropyDeviceData(navigatorObj))
  }
  if (config.enable_location_tracking) {
    Object.assign(payload, await collectLocation(navigatorObj))
  }

  sendTrackingBeacon(payload, { navigatorObj, fetchImpl })
  trackingReady = true
  flushPendingPageView()
  return true
}
