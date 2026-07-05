import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
  download: vi.fn(),
}

vi.mock('../client', () => calls)

describe('share API helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('posts unlock requests to the share unlock endpoint', async () => {
    const { unlockShareAccess } = await import('../share.js')
    calls.post.mockResolvedValueOnce({ unlocked: true })

    await unlockShareAccess('share-token', 'OpenSesame!1')

    expect(calls.post).toHaveBeenCalledWith('/share/share-token/unlock', {
      password: 'OpenSesame!1',
    })
  })
})
