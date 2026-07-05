import { describe, expect, it } from 'vitest'
import { buildAuthenticatedPreviewUrl, buildPreviewSrcdoc } from './preview'

describe('preview helpers', () => {
  it('builds API preview URL with auth token for iframe/native browser requests', () => {
    const url = buildAuthenticatedPreviewUrl('file-1', 2, 'jwt-token', 'v2-refresh')
    expect(url).toBe('/api/v1/files/file-1/preview?version=2&auth_token=jwt-token&_preview=v2-refresh')
  })

  it('injects auth token into lazy page image URLs inside skeleton HTML', () => {
    const html = '<html><body><img src="/api/v1/files/file-1/pages/1?version=2"><img src="/api/v1/files/file-1/pages/2"></body></html>'
    const srcdoc = buildPreviewSrcdoc(html, 'jwt token')
    expect(srcdoc).toContain('/api/v1/files/file-1/pages/1?version=2&amp;auth_token=jwt+token')
    expect(srcdoc).toContain('/api/v1/files/file-1/pages/2?auth_token=jwt+token')
  })
})


import { shouldShowPreviewFrame } from './preview'

describe('preview visibility', () => {
  it('shows iframe container when html srcdoc exists even without a URL', () => {
    expect(shouldShowPreviewFrame('<html>doc</html>', '')).toBe(true)
  })
})
