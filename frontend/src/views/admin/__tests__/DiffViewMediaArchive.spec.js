import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DiffView from '../DiffView.vue'
import { getFileVersions } from '@/api/file'
import { getDiffs } from '@/api/diff'

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'project-1', fileId: 'file-1' },
  }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

vi.mock('@/api/file', () => ({
  getFileVersions: vi.fn(),
  downloadVersion: vi.fn(),
}))

vi.mock('@/api/diff', () => ({
  getDiffs: vi.fn(),
}))

const stubs = {
  DiffSummary: { template: '<div class="summary-stub" />' },
  DocxDiffView: { template: '<div class="docx-stub" />', props: ['diffData'] },
  XlsxDiffView: { template: '<div class="xlsx-stub" />', props: ['diffData'] },
  PdfDiffView: { template: '<div class="pdf-stub" />', props: ['diffData'] },
  ElSelect: { template: '<div class="el-select"><slot /></div>', props: ['modelValue'] },
  ElOption: { template: '<span class="el-option" />', props: ['label', 'value'] },
}

describe('admin DiffView media and archive rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the media diff view when diff_type is media', async () => {
    getFileVersions.mockResolvedValue({
      file_type: 'mp4',
      filename: 'demo.mp4',
      versions: [
        { id: 1, version: 1, created_at: '2026-06-01T00:00:00Z' },
        { id: 2, version: 2, created_at: '2026-06-02T00:00:00Z' },
      ],
    })
    getDiffs.mockResolvedValue({
      diffs: [{
        summary: '媒体差异',
        diff_type: 'media',
        diff_data: {
          payload: {
            left: { preview_url: '/left.mp4' },
            right: { preview_url: '/right.mp4' },
          },
          summary: {
            duration_delta_seconds: 3,
            size_delta_bytes: 1024,
          },
        },
      }],
    })

    const wrapper = mount(DiffView, {
      global: {
        stubs,
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('媒体差异')
    expect(wrapper.find('.media-diff-view').exists()).toBe(true)
  })

  it('renders the archive diff view when diff_type is structure', async () => {
    getFileVersions.mockResolvedValue({
      file_type: 'zip',
      filename: 'bundle.zip',
      versions: [
        { id: 1, version: 1, created_at: '2026-06-01T00:00:00Z' },
        { id: 2, version: 2, created_at: '2026-06-02T00:00:00Z' },
      ],
    })
    getDiffs.mockResolvedValue({
      diffs: [{
        summary: '结构差异',
        diff_type: 'structure',
        diff_data: {
          payload: {
            added_paths: ['docs/readme.md'],
            removed_paths: ['old/data.csv'],
          },
          summary: {
            files_added: 1,
            files_removed: 1,
          },
        },
      }],
    })

    const wrapper = mount(DiffView, {
      global: {
        stubs,
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('结构差异')
    expect(wrapper.find('.archive-diff-view').exists()).toBe(true)
  })
})
