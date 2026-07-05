import { beforeEach, describe, expect, it, vi } from 'vitest'

const shareApiMocks = vi.hoisted(() => ({
  unlockShareAccess: vi.fn(),
  heartbeatShareAccess: vi.fn(),
  releaseShareAccess: vi.fn(),
}))

vi.mock('@/api/share', () => ({
  unlockShareAccess: shareApiMocks.unlockShareAccess,
  heartbeatShareAccess: shareApiMocks.heartbeatShareAccess,
  releaseShareAccess: shareApiMocks.releaseShareAccess,
}))

describe('useShareSession helpers', () => {
  beforeEach(() => {
    vi.resetModules()
    sessionStorage.clear()
    shareApiMocks.unlockShareAccess.mockReset()
    shareApiMocks.heartbeatShareAccess.mockReset()
    shareApiMocks.releaseShareAccess.mockReset()
  })

  it('reuses the same share_tab_id across refreshes in one tab', async () => {
    const { ensureShareTabId } = await import('@/composables/useShareSession.js')

    const first = ensureShareTabId()
    const second = ensureShareTabId()

    expect(second).toBe(first)
    expect(sessionStorage.getItem('docshop_share_tab_id')).toBe(first)
  })

  it('stores the returned grant token after unlock and injects share headers', async () => {
    shareApiMocks.unlockShareAccess.mockResolvedValueOnce({
      unlocked: true,
      grant_token: 'grant-1',
      heartbeat_interval_seconds: 30,
    })

    const { useShareSession } = await import('@/composables/useShareSession.js')
    const session = useShareSession('share-token')

    await session.unlock('OpenSesame!1')

    expect(shareApiMocks.unlockShareAccess).toHaveBeenCalledWith(
      'share-token',
      'OpenSesame!1',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Share-Tab-Id': session.tabId,
        }),
      }),
    )
    expect(session.grantToken.value).toBe('grant-1')
    expect(session.withShareHeaders()).toEqual({
      'X-Share-Tab-Id': session.tabId,
      'X-Share-Grant': 'grant-1',
    })
    expect(sessionStorage.getItem('docshop_share_grant:share-token')).toBe('grant-1')
  })

  it('clears the stored grant after release resolves', async () => {
    shareApiMocks.releaseShareAccess.mockResolvedValueOnce({ released: true })

    const { useShareSession } = await import('@/composables/useShareSession.js')
    sessionStorage.setItem('docshop_share_grant:share-token', 'grant-1')

    const session = useShareSession('share-token')
    await session.release()

    expect(shareApiMocks.releaseShareAccess).toHaveBeenCalledWith(
      'share-token',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Share-Tab-Id': session.tabId,
          'X-Share-Grant': 'grant-1',
        }),
      }),
    )
    expect(session.grantToken.value).toBe('')
    expect(sessionStorage.getItem('docshop_share_grant:share-token')).toBeNull()
  })

  it('uses a beacon-friendly release flow on pagehide and clears the grant immediately', async () => {
    const { useShareSession } = await import('@/composables/useShareSession.js')
    sessionStorage.setItem('docshop_share_grant:share-token', 'grant-1')

    const session = useShareSession('share-token')
    const navigatorObj = {
      sendBeacon: vi.fn(() => true),
    }
    const fetchImpl = vi.fn()

    const released = session.releaseOnPageHide({ navigatorObj, fetchImpl })

    expect(released).toBe(true)
    expect(navigatorObj.sendBeacon).toHaveBeenCalledTimes(1)
    const [url, body] = navigatorObj.sendBeacon.mock.calls[0]
    expect(url).toBe('/api/v1/share/share-token/grant/release')
    expect(body).toBeTruthy()
    if (typeof body !== 'string') {
      expect(String(body)).toBe('[object Blob]')
    }
    expect(fetchImpl).not.toHaveBeenCalled()
    expect(session.grantToken.value).toBe('')
    expect(sessionStorage.getItem('docshop_share_grant:share-token')).toBeNull()
  })
})
