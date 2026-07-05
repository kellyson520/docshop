import { describe, expect, it } from 'vitest'

import {
  buildShareAbsoluteUrl,
  buildShareDiffPath,
  buildShareFilePath,
  buildShareHomePath,
  buildSharePreviewPath,
} from '../shareRoute'

describe('shareRoute helpers', () => {
  it('builds canonical share page paths', () => {
    expect(buildShareHomePath('share-token')).toBe('/s/share-token')
    expect(buildShareFilePath('share-token', 'file-1')).toBe('/s/share-token/files/file-1')
    expect(buildSharePreviewPath('share-token', 'file-1')).toBe('/s/share-token/preview/file-1')
  })

  it('builds diff paths with optional query parameters', () => {
    expect(buildShareDiffPath('share-token', 'file-1')).toBe('/s/share-token/diff/file-1')
    expect(buildShareDiffPath('share-token', 'file-1', { version_id: 'ver-2' })).toBe(
      '/s/share-token/diff/file-1?version_id=ver-2',
    )
    expect(buildShareDiffPath('share-token', 'file-1', { version_id: 'ver-2', focus: 'summary' })).toBe(
      '/s/share-token/diff/file-1?version_id=ver-2&focus=summary',
    )
  })

  it('builds absolute share links against an explicit origin', () => {
    expect(buildShareAbsoluteUrl('share-token', 'http://localhost:3000')).toBe(
      'http://localhost:3000/s/share-token',
    )
  })

  it('returns empty strings when required route parameters are missing', () => {
    expect(buildShareHomePath('')).toBe('')
    expect(buildShareFilePath('share-token', '')).toBe('')
    expect(buildShareDiffPath('', 'file-1')).toBe('')
    expect(buildSharePreviewPath('share-token', '')).toBe('')
    expect(buildShareAbsoluteUrl('')).toBe('')
  })
})
