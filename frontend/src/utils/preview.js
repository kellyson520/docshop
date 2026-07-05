import { buildFilePreviewUrl } from './resourceUrl'

export function buildAuthenticatedPreviewUrl(fileId, version, token, cacheKey) {
  return buildFilePreviewUrl(fileId, {
    version,
    authToken: token,
    cacheKey,
  })
}

export function buildPreviewSrcdoc(html, token) {
  if (!html || !token) return html || ''
  return html.replace(/(src=["'])(\/api\/v1\/files\/[^"']+?\/pages\/\d+)(\?[^"']*)?(["'])/g, (_match, prefix, base, query = '', suffix) => {
    const params = new URLSearchParams((query || '').replace(/^\?/, ''))
    params.set('auth_token', token)
    return `${prefix}${base}?${params.toString().replace(/&/g, '&amp;')}${suffix}`
  })
}


export function shouldShowPreviewFrame(html, url) {
  return Boolean((typeof html === 'string' && html.length > 0) || (typeof url === 'string' && url.length > 0))
}
