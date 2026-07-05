import { ref } from 'vue'
import {
  heartbeatPublicAccess,
  releasePublicAccess,
  unlockPublicAccess,
} from '@/api/accessControl'

export const PUBLIC_ACCESS_TAB_STORAGE_KEY = 'docshop_public_access_tab_id'
export const PUBLIC_ACCESS_GRANT_PREFIX = 'docshop_public_access_grant:'

function resolveSessionStorage(sessionStorageObj) {
  if (sessionStorageObj) return sessionStorageObj
  if (typeof window !== 'undefined' && window.sessionStorage) {
    return window.sessionStorage
  }
  return {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  }
}

function createAccessTabId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `public-access-tab-${Math.random().toString(36).slice(2, 10)}`
}

function grantStorageKey(shareToken, resourceType, resourceId) {
  return `${PUBLIC_ACCESS_GRANT_PREFIX}${String(shareToken || '')}:${String(resourceType || '')}:${String(resourceId || '')}`
}

export function ensurePublicAccessTabId(sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const existing = String(storage.getItem(PUBLIC_ACCESS_TAB_STORAGE_KEY) || '').trim()
  if (existing) return existing

  const tabId = createAccessTabId()
  storage.setItem(PUBLIC_ACCESS_TAB_STORAGE_KEY, tabId)
  return tabId
}

export function readPublicAccessGrant(shareToken, resourceType, resourceId, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  return String(storage.getItem(grantStorageKey(shareToken, resourceType, resourceId)) || '')
}

export function writePublicAccessGrant(shareToken, resourceType, resourceId, grant, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const normalizedGrant = String(grant || '').trim()
  const key = grantStorageKey(shareToken, resourceType, resourceId)
  if (!normalizedGrant) {
    storage.removeItem(key)
    return ''
  }
  storage.setItem(key, normalizedGrant)
  return normalizedGrant
}

export function clearPublicAccessGrant(shareToken, resourceType, resourceId, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  storage.removeItem(grantStorageKey(shareToken, resourceType, resourceId))
}

export function isResourcePasswordRequiredError(err) {
  return err?.response?.data?.detail === 'resource_password_required'
}

export function getUnlockErrorMessage(err) {
  return err?.response?.data?.detail === 'resource_password_invalid'
    ? '访问密码错误，请重试'
    : '资源解锁失败，请稍后重试'
}

export function usePublicAccessSession(
  shareToken,
  resourceType,
  resourceId,
  sessionStorageObj = resolveSessionStorage(),
) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const tabId = ensurePublicAccessTabId(storage)
  const grantToken = ref(readPublicAccessGrant(shareToken, resourceType, resourceId, storage))

  function clearActiveGrant() {
    clearPublicAccessGrant(shareToken, resourceType, resourceId, storage)
    grantToken.value = ''
  }

  function withAccessHeaders(headers = {}) {
    return {
      ...headers,
      'X-Access-Tab-Id': tabId,
      ...(grantToken.value ? { 'X-Access-Grant': grantToken.value } : {}),
    }
  }

  function buildPayload(password = undefined) {
    return {
      resource_type: resourceType,
      resource_id: resourceId,
      ...(password !== undefined ? { password } : {}),
    }
  }

  async function unlock(password) {
    const payload = await unlockPublicAccess(
      shareToken,
      buildPayload(password),
      {
        headers: withAccessHeaders(),
      },
    )

    const nextGrant = writePublicAccessGrant(shareToken, resourceType, resourceId, payload?.grant_token, storage)
    grantToken.value = nextGrant
    return payload
  }

  async function heartbeat() {
    if (!grantToken.value) {
      return { active: false }
    }

    const payload = await heartbeatPublicAccess(
      shareToken,
      buildPayload(),
      {
        headers: withAccessHeaders(),
      },
    )

    const nextGrant = String(payload?.grant_token || grantToken.value || '')
    grantToken.value = writePublicAccessGrant(shareToken, resourceType, resourceId, nextGrant, storage)
    return payload
  }

  async function release() {
    const headers = withAccessHeaders()
    if (grantToken.value) {
      try {
        await releasePublicAccess(shareToken, buildPayload(), { headers })
      } finally {
        clearActiveGrant()
      }
      return { released: true }
    }

    clearActiveGrant()
    return { released: false }
  }

  function releaseOnPageHide({
    navigatorObj = navigator,
    fetchImpl = fetch,
  } = {}) {
    const currentGrant = String(grantToken.value || '').trim()
    if (!currentGrant) {
      clearActiveGrant()
      return false
    }

    const url = `/api/v1/share/${shareToken}/public-access/grant/release`
    const payload = JSON.stringify({
      resource_type: resourceType,
      resource_id: resourceId,
      tab_id: tabId,
      grant_token: currentGrant,
    })

    let dispatched = false

    try {
      const beaconBody = typeof Blob !== 'undefined'
        ? new Blob([payload], { type: 'application/json' })
        : payload

      if (navigatorObj?.sendBeacon?.(url, beaconBody)) {
        dispatched = true
      } else if (typeof fetchImpl === 'function') {
        fetchImpl(url, {
          method: 'POST',
          body: payload,
          headers: { 'Content-Type': 'application/json' },
          keepalive: true,
          credentials: 'include',
        }).catch(() => {})
        dispatched = true
      }
    } finally {
      clearActiveGrant()
    }

    return dispatched
  }

  return {
    tabId,
    grantToken,
    unlock,
    heartbeat,
    release,
    releaseOnPageHide,
    withAccessHeaders,
    isResourcePasswordRequiredError,
    getUnlockErrorMessage,
  }
}
