import { beforeEach, describe, expect, it, vi } from 'vitest'

const shareApiMocks = vi.hoisted(() => ({
  issueShareResourceTicket: vi.fn(),
}))

vi.mock('@/api/share', () => ({
  issueShareResourceTicket: shareApiMocks.issueShareResourceTicket,
}))

describe('shareResourceTickets', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('requests a resource ticket for unlocked password shares and returns a ticketized preview url', async () => {
    const { getShareResourceUrl } = await import('../shareResourceTickets')
    shareApiMocks.issueShareResourceTicket.mockResolvedValue({ ticket: 'ticket-preview' })

    const url = await getShareResourceUrl({
      token: 'share-token',
      session: {
        grantToken: { value: 'grant-1' },
        withShareHeaders: () => ({
          'X-Share-Tab-Id': 'tab-a',
          'X-Share-Grant': 'grant-1',
        }),
      },
      kind: 'preview',
      fileId: 'file-1',
    })

    expect(shareApiMocks.issueShareResourceTicket).toHaveBeenCalledWith(
      'share-token',
      expect.objectContaining({
        kind: 'preview',
        file_id: 'file-1',
      }),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Share-Tab-Id': 'tab-a',
          'X-Share-Grant': 'grant-1',
        }),
      }),
    )
    expect(url).toBe('/api/v1/share/share-token/files/file-1/preview?ticket=ticket-preview')
  })

  it('falls back to direct share urls when no tab grant is active', async () => {
    const { getShareResourceUrl } = await import('../shareResourceTickets')

    const url = await getShareResourceUrl({
      token: 'share-token',
      session: {
        grantToken: { value: '' },
        withShareHeaders: () => ({
          'X-Share-Tab-Id': 'tab-a',
        }),
      },
      kind: 'download_original',
      fileId: 'file-1',
      versionId: 'version-1',
    })

    expect(shareApiMocks.issueShareResourceTicket).not.toHaveBeenCalled()
    expect(url).toBe('/api/v1/share/share-token/files/file-1/versions/version-1/download')
  })

  it('uses public-access headers when a legacy public resource grant is active', async () => {
    const { getShareResourceUrl } = await import('../shareResourceTickets')
    shareApiMocks.issueShareResourceTicket.mockResolvedValue({ ticket: 'ticket-preview' })

    const url = await getShareResourceUrl({
      token: 'share-token',
      session: {
        grantToken: { value: '' },
        withShareHeaders: () => ({ 'X-Share-Tab-Id': 'tab-a' }),
      },
      accessSession: {
        grantToken: { value: 'access-grant-1' },
        withAccessHeaders: () => ({
          'X-Access-Tab-Id': 'tab-a',
          'X-Access-Grant': 'access-grant-1',
        }),
      },
      kind: 'preview',
      fileId: 'file-1',
    })

    expect(shareApiMocks.issueShareResourceTicket).toHaveBeenCalledWith(
      'share-token',
      expect.objectContaining({
        kind: 'preview',
        file_id: 'file-1',
      }),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Access-Tab-Id': 'tab-a',
          'X-Access-Grant': 'access-grant-1',
        }),
      }),
    )
    expect(url).toBe('/api/v1/share/share-token/files/file-1/preview?ticket=ticket-preview')
  })
})
