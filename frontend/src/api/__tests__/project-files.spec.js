import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}

vi.mock('../client', () => calls)

describe('project file API helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches project files with keyword query params', async () => {
    const { getProjectFiles } = await import('../project.js')
    calls.get.mockResolvedValueOnce({ files: [] })

    await getProjectFiles('project-1', { keyword: 'budget' })

    expect(calls.get).toHaveBeenCalledWith('/projects/project-1/files', { keyword: 'budget' })
  })
})
