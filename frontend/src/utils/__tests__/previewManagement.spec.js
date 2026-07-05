import { describe, expect, it } from 'vitest'

import {
  buildShareUrl,
  indexLatestShareTokensByResource,
  mergeCreatedShareToken,
  normalizePreviewStatusRow,
  previewStatusLabel,
  shareResourceKey,
} from '../previewManagement'

describe('preview/share management helpers', () => {
  it('normalizes unknown preview status into actionable missing state', () => {
    const row = normalizePreviewStatusRow(
      { id: 'f1', file_type: 'docx' },
      { status: 'unknown', progress: 42, storage_bytes: 12 }
    )

    expect(row.status).toBe('missing')
    expect(row.stage).toBe('预览状态未知，需重新生成')
    expect(previewStatusLabel(row.status)).toBe('缺失')
  })

  it('keeps detailed progress fields for active preview rows', () => {
    const row = normalizePreviewStatusRow(
      { id: 'f2', file_type: 'pdf' },
      { status: 'images_generating', progress: 77, page_count: 20, rendered_pages: 9, pdf_bytes: 100, image_bytes: 200 }
    )

    expect(row.status).toBe('images_generating')
    expect(row.progress).toBe(77)
    expect(row.page_count).toBe(20)
    expect(row.rendered_pages).toBe(9)
    expect(row.pdf_bytes).toBe(100)
    expect(row.image_bytes).toBe(200)
  })

  it('updates project and file share tracking after a token is created', () => {
    const project = { id: 'p1', share_token: 'old-token' }
    const files = [{ id: 'f1' }, { id: 'f2' }]
    const shareTokensByResource = {}

    const nextProjectState = mergeCreatedShareToken({
      project,
      files,
      shareTokensByResource,
      tokenPayload: { token: 'project-token', resource_type: 'project', resource_id: 'p1', share_url: '/s/project-token' },
    })

    expect(nextProjectState.project.share_token).toBe('project-token')
    expect(nextProjectState.shareTokensByResource[shareResourceKey('project', 'p1')].token).toBe('project-token')

    const nextFileState = mergeCreatedShareToken({
      project: nextProjectState.project,
      files: nextProjectState.files,
      shareTokensByResource: nextProjectState.shareTokensByResource,
      tokenPayload: { token: 'file-token', resource_type: 'file', resource_id: 'f2' },
    })

    expect(nextFileState.files.find((file) => file.id === 'f2').share_token).toBe('file-token')
    expect(nextFileState.shareTokensByResource[shareResourceKey('file', 'f2')].token).toBe('file-token')
    expect(buildShareUrl('file-token', 'http://localhost:3000')).toBe('http://localhost:3000/s/file-token')
  })

  it('indexes the latest share token per resource for in-place permission editing', () => {
    const indexed = indexLatestShareTokensByResource([
      {
        id: 'old-file-token',
        token: 'old-file-token',
        resource_type: 'file',
        resource_id: 'f2',
        updated_at: '2026-07-01T08:00:00Z',
      },
      {
        id: 'new-file-token',
        token: 'new-file-token',
        resource_type: 'file',
        resource_id: 'f2',
        updated_at: '2026-07-02T08:00:00Z',
      },
      {
        id: 'project-token',
        token: 'project-token',
        resource_type: 'project',
        resource_id: 'p1',
        created_at: '2026-07-03T08:00:00Z',
      },
    ])

    expect(indexed[shareResourceKey('file', 'f2')].id).toBe('new-file-token')
    expect(indexed[shareResourceKey('project', 'p1')].id).toBe('project-token')
  })
})
