const URL_TOKEN_KEYS = ['token', 'access_token']
export const ACCESS_DENIED_PATH = '/access-denied'
export const URL_ACCESS_TOKEN_STORAGE_KEY = 'docshop_access_token'

export function getStoredLoginToken() {
  return localStorage.getItem('access_token') || ''
}

export function getStoredUrlAccessToken() {
  return localStorage.getItem(URL_ACCESS_TOKEN_STORAGE_KEY) || ''
}

export function getUrlAccessToken(route) {
  const paramToken = route?.params?.token
  if (typeof paramToken === 'string' && paramToken.trim()) return paramToken.trim()

  for (const key of URL_TOKEN_KEYS) {
    const value = route?.query?.[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (Array.isArray(value)) {
      const first = value.find((item) => typeof item === 'string' && item.trim())
      if (first) return first.trim()
    }
  }

  return ''
}

export function isShareTokenRoute(route) {
  return typeof route?.params?.token === 'string' && route.params.token.trim() && String(route?.path || '').startsWith('/s/')
}

export function persistUrlAccessToken(token) {
  if (!token) return
  localStorage.setItem(URL_ACCESS_TOKEN_STORAGE_KEY, token)
}

export function clearUrlTokenQuery(query = {}) {
  const clean = { ...query }
  for (const key of URL_TOKEN_KEYS) {
    delete clean[key]
  }
  return clean
}

export function hasUrlTokenQuery(query = {}) {
  return URL_TOKEN_KEYS.some((key) => query?.[key] !== undefined)
}

export function canPassGlobalAccessGate(route) {
  if (route?.path === '/login') return true
  if (route?.path === ACCESS_DENIED_PATH) return true
  return Boolean(getStoredLoginToken() || getUrlAccessToken(route) || getStoredUrlAccessToken())
}

export function getAccessDeniedRedirect(route, reason = 'missing_credentials') {
  return {
    path: ACCESS_DENIED_PATH,
    query: {
      redirect: route?.fullPath || route?.path || '/',
      reason
    }
  }
}

export async function validateUrlAccessToken(token, fetchImpl = fetch) {
  if (!token) return false
  try {
    const response = await fetchImpl('/api/v1/access-tokens/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    })
    if (!response?.ok) return false
    const body = await response.json()
    const data = body?.data || body
    return data?.valid === true
  } catch {
    return false
  }
}

export async function canPassGlobalAccessGateVerified(route, fetchImpl = fetch) {
  if (route?.path === '/login') return true
  if (route?.path === ACCESS_DENIED_PATH) return true
  if (getStoredLoginToken()) return true
  if (isShareTokenRoute(route)) return true

  const token = getUrlAccessToken(route) || getStoredUrlAccessToken()
  if (!token) return false

  const valid = await validateUrlAccessToken(token, fetchImpl)
  if (valid) {
    persistUrlAccessToken(token)
    return true
  }

  localStorage.removeItem(URL_ACCESS_TOKEN_STORAGE_KEY)
  return false
}
