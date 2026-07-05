import { beforeEach, describe, expect, it, vi } from 'vitest'

const accessApiMocks = vi.hoisted(() => ({
  unlockPublicAccess: vi.fn(),
  heartbeatPublicAccess: vi.fn(),
  releasePublicAccess: vi.fn(),
}))

vi.mock('@/api/accessControl', () => ({
  unlockPublicAccess: accessApiMocks.unlockPublicAccess,
  heartbeatPublicAccess: accessApiMocks.heartbeatPublicAccess,
  releasePublicAccess: accessApiMocks.releasePublicAccess,
}))

describe('usePublicAccessSession helpers', () => {
  beforeEach(() => {
    vi.resetModules()
    sessionStorage.clear()
    accessApiMocks.unlockPublicAccess.mockReset()
    accessApiMocks.heartbeatPublicAccess.mockReset()
    accessApiMocks.releasePublicAccess.mockReset()
  })

  it('stores public access grant by resource and injects access headers', async () => {
    accessApiMocks.unlockPublicAccess.mockResolvedValueOnce({
      unlocked: true,
      grant_token: 'access-grant-1',
      heartbeat_interval_seconds: 30,
    })

    const { usePublicAccessSession } = await import('@/composables/usePublicAccessSession.js')
    const session = usePublicAccessSession('share-token', 'file', 'file-1')

    await session.unlock('OpenSesame!1')

    expect(accessApiMocks.unlockPublicAccess).toHaveBeenCalledWith(
      'share-token',
      {
        resource_type: 'file',
        resource_id: 'file-1',
        password: 'OpenSesame!1',
      },
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Access-Tab-Id': session.tabId,
        }),
      }),
    )
    expect(session.grantToken.value).toBe('access-grant-1')
    expect(session.withAccessHeaders()).toEqual({
      'X-Access-Tab-Id': session.tabId,
      'X-Access-Grant': 'access-grant-1',
    })
    expect(sessionStorage.getItem('docshop_public_access_grant:share-token:file:file-1')).toBe('access-grant-1')
  })

  it('releases public access on pagehide and clears the stored grant immediately', async () => {
    const { usePublicAccessSession } = await import('@/composables/usePublicAccessSession.js')
    sessionStorage.setItem('docshop_public_access_grant:share-token:file:file-1', 'access-grant-1')

    const session = usePublicAccessSession('share-token', 'file', 'file-1')
    const navigatorObj = {
      sendBeacon: vi.fn(() => true),
    }
    const fetchImpl = vi.fn()

    const released = session.releaseOnPageHide({ navigatorObj, fetchImpl })

    expect(released).toBe(true)
    expect(navigatorObj.sendBeacon).toHaveBeenCalledTimes(1)
    const [url, body] = navigatorObj.sendBeacon.mock.calls[0]
    expect(url).toBe('/api/v1/share/share-token/public-access/grant/release')
    expect(body).toBeTruthy()
    expect(fetchImpl).not.toHaveBeenCalled()
    expect(session.grantToken.value).toBe('')
    expect(sessionStorage.getItem('docshop_public_access_grant:share-token:file:file-1')).toBeNull()
  })
})
