import { describe, expect, it } from 'vitest'

import {
  buildAnnouncementAttachmentUrl,
  buildFileDownloadUrl,
  buildFilePageUrl,
  buildFilePreviewAssetUrl,
  buildFilePreviewUrl,
  buildShareDownloadUrl,
  buildShareFolderDownloadUrl,
  buildSharePageUrl,
  buildSharePreviewAssetUrl,
  buildSharePreviewUrl,
  isExternalUrl,
  normalizePath,
  resolveAvatarUrl,
  resolveCoverUrl,
  withQuery,
} from '../resourceUrl'

describe('resourceUrl', () => {
  it('normalizes browser-facing avatar and cover asset urls', () => {
    expect(resolveAvatarUrl('avatars/u/a.png')).toBe('/api/v1/avatars/u/a.png')
    expect(resolveCoverUrl('/covers/c.png')).toBe('/api/v1/covers/c.png')
    expect(resolveCoverUrl('C:\\docshop\\data\\covers\\card-1\\cover.png')).toBe('/api/v1/covers/card-1/cover.png')
  })

  it('keeps external or browser-generated urls unchanged', () => {
    expect(resolveAvatarUrl('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png')
    expect(resolveCoverUrl('data:image/png;base64,abc')).toBe('data:image/png;base64,abc')
    expect(resolveCoverUrl('blob:https://example.com/id')).toBe('blob:https://example.com/id')
  })

  it('builds file preview, page, asset and download urls', () => {
    expect(buildFilePreviewUrl('f1', {
      version: 2,
      authToken: 'tok',
      cacheKey: 'c',
    })).toBe('/api/v1/files/f1/preview?version=2&auth_token=tok&_preview=c')
    expect(buildFilePageUrl('f1', 3, { version: 2, authToken: 'tok' }))
      .toBe('/api/v1/files/f1/pages/3?version=2&auth_token=tok')
    expect(buildFilePreviewAssetUrl('f1', 'a1'))
      .toBe('/api/v1/files/f1/preview-assets/a1')
    expect(buildFileDownloadUrl('f1')).toBe('/api/v1/files/f1/download')
    expect(buildFileDownloadUrl('f1', 'v1')).toBe('/api/v1/files/f1/versions/v1/download')
    expect(buildFileDownloadUrl('f1', 'v1', 'pdf')).toBe('/api/v1/files/f1/versions/v1/download/pdf')
  })

  it('builds share preview, page, asset and download urls', () => {
    expect(buildSharePreviewUrl('s1', 'f1')).toBe('/api/v1/share/s1/files/f1/preview')
    expect(buildSharePageUrl('s1', 'f1', 3, { version: 2, authToken: 'tok' }))
      .toBe('/api/v1/share/s1/files/f1/pages/3?version=2&auth_token=tok')
    expect(buildSharePreviewAssetUrl('s1', 'f1', 'a1'))
      .toBe('/api/v1/share/s1/files/f1/preview-assets/a1')
    expect(buildShareDownloadUrl('s1', 'f1', 'v1', 'pdf'))
      .toBe('/api/v1/share/s1/files/f1/versions/v1/download/pdf')
    expect(buildShareFolderDownloadUrl('s1', 'folder1'))
      .toBe('/api/v1/share/s1/folders/folder1/download')
  })

  it('adds share resource tickets to browser-native share urls', () => {
    expect(buildSharePreviewUrl('s1', 'f1', { ticket: 'ticket-1' }))
      .toBe('/api/v1/share/s1/files/f1/preview?ticket=ticket-1')
    expect(buildSharePageUrl('s1', 'f1', 3, { ticket: 'ticket-2' }))
      .toBe('/api/v1/share/s1/files/f1/pages/3?ticket=ticket-2')
    expect(buildSharePreviewAssetUrl('s1', 'f1', 'a1', { ticket: 'ticket-3' }))
      .toBe('/api/v1/share/s1/files/f1/preview-assets/a1?ticket=ticket-3')
    expect(buildShareDownloadUrl('s1', 'f1', 'v1', 'pdf', { ticket: 'ticket-4' }))
      .toBe('/api/v1/share/s1/files/f1/versions/v1/download/pdf?ticket=ticket-4')
    expect(buildShareFolderDownloadUrl('s1', 'folder1', { ticket: 'ticket-5' }))
      .toBe('/api/v1/share/s1/folders/folder1/download?ticket=ticket-5')
  })

  it('builds announcement attachment urls via the common file download path', () => {
    expect(buildAnnouncementAttachmentUrl('file1')).toBe('/api/v1/files/file1/download')
  })

  it('exports low-level normalization helpers', () => {
    expect(normalizePath('C:\\temp\\avatars\\u.png')).toBe('C:/temp/avatars/u.png')
    expect(isExternalUrl('https://example.com/file.png')).toBe(true)
    expect(isExternalUrl('/api/v1/files/f1/preview')).toBe(false)
    expect(withQuery('/api/v1/files/f1/preview', { version: 2, empty: '' }))
      .toBe('/api/v1/files/f1/preview?version=2')
  })
})
