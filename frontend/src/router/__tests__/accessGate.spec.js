
import { describe, it, expect, beforeEach } from 'vitest'
import { getUrlAccessToken, canPassGlobalAccessGate, canPassGlobalAccessGateVerified, ACCESS_DENIED_PATH, getAccessDeniedRedirect } from '../accessGate.js'

describe('global access gate', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('blocks homepage when visitor has neither login token nor URL token', () => {
    expect(canPassGlobalAccessGate({ path: '/', query: {}, params: {} })).toBe(false)
  })



  it('allows the access denied page itself without login or URL token', () => {
    expect(canPassGlobalAccessGate({ path: ACCESS_DENIED_PATH, query: {}, params: {} })).toBe(true)
  })

  it('builds access denied redirect with original target and reason', () => {
    expect(getAccessDeniedRedirect({ fullPath: '/admin/projects?keyword=a' })).toEqual({
      path: ACCESS_DENIED_PATH,
      query: {
        redirect: '/admin/projects?keyword=a',
        reason: 'missing_credentials'
      }
    })
  })

  it('allows homepage when URL carries an access token', () => {
    expect(canPassGlobalAccessGate({ path: '/', query: { token: 'share-token' }, params: {} })).toBe(true)
  })

  it('allows share route when token is in path params', () => {
    expect(canPassGlobalAccessGate({ path: '/s/share-token', query: {}, params: { token: 'share-token' } })).toBe(true)
  })

  it('allows logged-in users without URL token', () => {
    localStorage.setItem('access_token', 'jwt-token')

    expect(canPassGlobalAccessGate({ path: '/', query: {}, params: {} })).toBe(true)
  })

  it('extracts token query aliases', () => {
    expect(getUrlAccessToken({ query: { token: 'abc' }, params: {} })).toBe('abc')
    expect(getUrlAccessToken({ query: { access_token: 'def' }, params: {} })).toBe('def')
  })

  it('verifies URL token against access-token management endpoint', async () => {
    const fetchImpl = async (url, options) => {
      expect(url).toBe('/api/v1/access-tokens/validate')
      expect(JSON.parse(options.body)).toEqual({ token: 'managed-token' })
      return {
        ok: true,
        json: async () => ({ code: 0, data: { valid: true } })
      }
    }

    await expect(canPassGlobalAccessGateVerified({
      path: '/',
      query: { token: 'managed-token' },
      params: {}
    }, fetchImpl)).resolves.toBe(true)
  })

  it('rejects invalid URL token from access-token management endpoint', async () => {
    const fetchImpl = async () => ({
      ok: true,
      json: async () => ({ code: 0, data: { valid: false } })
    })

    await expect(canPassGlobalAccessGateVerified({
      path: '/',
      query: { token: 'bad-token' },
      params: {}
    }, fetchImpl)).resolves.toBe(false)
  })
})
