
import { describe, expect, it } from 'vitest'
import { projectCoverKey, projectCoverUrl } from '../projectCover.js'

describe('projectCover', () => {
  it('uses matched file as stable cover key when search hits a file', () => {
    expect(projectCoverKey({ id: 'p1', matched_file: { id: 'f2' }, first_file: { id: 'f1' } })).toBe('f2')
  })

  it('returns empty cover after image load failed so UI can show fallback', () => {
    const project = { id: 'p1', cover_image: '/api/v1/covers/missing.png', matched_file: { id: 'f2' } }
    const failed = new Set(['f2'])

    expect(projectCoverUrl(project, failed)).toBe('')
  })
})
