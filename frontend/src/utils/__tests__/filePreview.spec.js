import { describe, expect, it } from 'vitest'
import { buildClientPreviewManifest, deriveClientProfile } from '../filePreview'

describe('filePreview helpers', () => {
  it('derives archive capabilities for 7z files', () => {
    const profile = deriveClientProfile('bundle.7z')

    expect(profile.category).toBe('archive')
    expect(profile.preview_mode).toBe('structure')
    expect(profile.can_preview).toBe(true)
    expect(profile.can_diff_structural).toBe(true)
  })

  it('derives archive capabilities for tgz files', () => {
    const profile = deriveClientProfile('bundle.tgz')

    expect(profile.ext).toBe('tgz')
    expect(profile.category).toBe('archive')
    expect(profile.preview_mode).toBe('structure')
    expect(profile.can_preview).toBe(true)
    expect(profile.can_diff_structural).toBe(true)
  })

  it('builds an office preview manifest for docx files', () => {
    const manifest = buildClientPreviewManifest({ filename: 'brief.docx' }, { page_count: 8 })

    expect(manifest.type).toBe('office_pdf')
    expect(manifest.status).toBe('ready')
    expect(manifest.summary.page_count).toBe(8)
  })

  it('derives html capabilities and builds an html preview manifest', () => {
    const profile = deriveClientProfile('MATLAB模拟测试.html')
    const manifest = buildClientPreviewManifest({ filename: 'MATLAB模拟测试.html' }, { title: 'MATLAB模拟测试' })

    expect(profile.category).toBe('html')
    expect(profile.preview_mode).toBe('native')
    expect(profile.can_preview).toBe(true)
    expect(manifest.type).toBe('html_runtime')
    expect(manifest.status).toBe('ready')
    expect(manifest.summary.title).toBe('MATLAB模拟测试')
  })
})
