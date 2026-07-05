import { ref } from 'vue'
import {
  heartbeatShareAccess,
  releaseShareAccess,
  unlockShareAccess,
} from '@/api/share'

export const SHARE_TAB_STORAGE_KEY = 'docshop_share_tab_id'
export const SHARE_GRANT_PREFIX = 'docshop_share_grant:'

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

function createShareTabId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `share-tab-${Math.random().toString(36).slice(2, 10)}`
}

function grantStorageKey(token) {
  return `${SHARE_GRANT_PREFIX}${String(token || '')}`
}

export function ensureShareTabId(sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const existing = String(storage.getItem(SHARE_TAB_STORAGE_KEY) || '').trim()
  if (existing) return existing

  const tabId = createShareTabId()
  storage.setItem(SHARE_TAB_STORAGE_KEY, tabId)
  return tabId
}

export function readShareGrant(token, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  return String(storage.getItem(grantStorageKey(token)) || '')
}

export function writeShareGrant(token, grant, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const normalizedGrant = String(grant || '').trim()
  if (!normalizedGrant) {
    storage.removeItem(grantStorageKey(token))
    return ''
  }
  storage.setItem(grantStorageKey(token), normalizedGrant)
  return normalizedGrant
}

export function clearShareGrant(token, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  storage.removeItem(grantStorageKey(token))
}

export function isPasswordRequiredError(err) {
  return err?.response?.data?.detail === 'share_password_required'
}

export function getUnlockErrorMessage(err) {
  return err?.response?.data?.detail === 'share_password_invalid'
    ? '密码错误，请重试'
    : '解锁失败，请稍后再试'
}

export function useShareSession(token, sessionStorageObj = resolveSessionStorage()) {
  const storage = resolveSessionStorage(sessionStorageObj)
  const tabId = ensureShareTabId(storage)
  const grantToken = ref(readShareGrant(token, storage))

  function clearActiveGrant() {
    clearShareGrant(token, storage)
    grantToken.value = ''
  }

  function withShareHeaders(headers = {}) {
    return {
      ...headers,
      'X-Share-Tab-Id': tabId,
      ...(grantToken.value ? { 'X-Share-Grant': grantToken.value } : {}),
    }
  }

  async function unlock(password) {
    const payload = await unlockShareAccess(token, password, {
      headers: withShareHeaders(),
    })

    const nextGrant = writeShareGrant(token, payload?.grant_token, storage)
    grantToken.value = nextGrant
    return payload
  }

  async function heartbeat() {
    if (!grantToken.value) {
      return { active: false }
    }

    const payload = await heartbeatShareAccess(token, {
      headers: withShareHeaders(),
    })

    const nextGrant = String(payload?.grant_token || grantToken.value || '')
    grantToken.value = writeShareGrant(token, nextGrant, storage)
    return payload
  }

  async function release() {
    const headers = withShareHeaders()
    if (grantToken.value) {
      try {
        await releaseShareAccess(token, { headers })
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

    const url = `/api/v1/share/${token}/grant/release`
    const payload = JSON.stringify({
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
    withShareHeaders,
    isPasswordRequiredError,
    getUnlockErrorMessage,
  }
}
