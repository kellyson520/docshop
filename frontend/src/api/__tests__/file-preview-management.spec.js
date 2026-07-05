import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = {
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
  upload: vi.fn(),
  download: vi.fn(),
}

vi.mock('../client', () => calls)

describe('preview management file API helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches admin preview statuses with filters', async () => {
    const { getPreviewStatuses } = await import('../file.js')
    calls.get.mockResolvedValueOnce({ files: [], summary: {} })

    await getPreviewStatuses({ project_id: 'p1', status: 'failed', file_type: 'pdf' })

    expect(calls.get).toHaveBeenCalledWith('/admin/files/previews', {
      project_id: 'p1',
      status: 'failed',
      file_type: 'pdf',
    })
  })

  it('queues preview generation with force flag', async () => {
    const { enqueuePreviewGeneration } = await import('../file.js')
    calls.post.mockResolvedValueOnce({ queued: 2 })

    await enqueuePreviewGeneration(['f1', 'f2'], { force: true })

    expect(calls.post).toHaveBeenCalledWith('/admin/files/preconvert', {
      file_ids: ['f1', 'f2'],
      force: true,
    })
  })

  it('clears one file preview cache', async () => {
    const { clearPreviewCache } = await import('../file.js')
    calls.del.mockResolvedValueOnce({ removed_bytes: 10 })

    await clearPreviewCache('f1')

    expect(calls.del).toHaveBeenCalledWith('/admin/files/f1/preview-cache')
  })

  it('cleans preview caches by status', async () => {
    const { cleanupPreviewCaches } = await import('../file.js')
    calls.post.mockResolvedValueOnce({ cleared: 1 })

    await cleanupPreviewCaches({ statuses: ['failed', 'interrupted'] })

    expect(calls.post).toHaveBeenCalledWith('/admin/files/preview-cache/cleanup', {
      statuses: ['failed', 'interrupted'],
    })
  })
})
