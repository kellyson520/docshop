import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

let DiffView

const mocks = {
  getFileVersions: vi.fn(),
  getDiffs: vi.fn(),
  buildAuthenticatedPreviewUrl: vi.fn((fileId, version, token, cacheKey) => (
    `/api/v1/files/${fileId}/preview?version=${version}&auth_token=${token}&_preview=${cacheKey}`
  )),
}

function mountDiffView() {
  return mount(DiffView, {
    global: {
      stubs: {
        DiffSummary: { template: '<div class="summary-stub" />' },
        DocxDiffView: { template: '<div class="docx-stub" />', props: ['diffData'] },
        HtmlDiffView: { template: '<div class="html-semantic-stub" />', props: ['diffData'] },
        XlsxDiffView: { template: '<div class="xlsx-stub" />', props: ['diffData'] },
        PdfDiffView: { template: '<div class="pdf-stub" />', props: ['diffData'] },
        ElSelect: { template: '<div class="el-select"><slot /></div>', props: ['modelValue'] },
        ElOption: { template: '<span class="el-option" />', props: ['label', 'value'] },
      },
      directives: { loading: {} },
    },
  })
}

describe('admin DiffView', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()

    localStorage.setItem('access_token', 'token-123')

    mocks.getFileVersions.mockResolvedValue({
      file_type: 'docx',
      filename: 'demo.docx',
      versions: [
        { id: 1, version: 1, created_at: '2026-06-01T00:00:00Z' },
        { id: 2, version: 2, created_at: '2026-06-02T00:00:00Z' },
      ],
    })
    mocks.getDiffs.mockResolvedValue({
      diffs: [{
        summary: '新增 1 段；2 个表格变化；4 处图片变化',
        diff_type: 'docx_diff',
        diff_data: {
          text: [{ change_type: 'insert', new_text: '新增段落' }],
          tables: [{ table_index: 0 }, { table_index: 1 }],
          images: {
            added: [{ filename: 'a.png' }],
            deleted: [{ filename: 'b.png' }],
            replaced: [{ filename: 'c.png' }],
            resized: [{ filename: 'd.png' }],
          },
          metadata: { elapsed_ms: 88, file_type: 'docx' },
          status: 'completed',
          stats: {
            text_changes: 1,
            text_added: 1,
            tables_changed: 2,
            image_added: 1,
            image_deleted: 1,
            image_replaced: 1,
            image_resized: 1,
            total_changes: 7,
          },
        },
      }],
    })

    vi.doMock('vue-router', () => ({
      useRoute: () => ({ params: { id: 'project-1', fileId: 'file-1' } }),
      useRouter: () => ({ push: vi.fn() }),
    }))

    vi.doMock('@/api/file', () => ({
      getFileVersions: mocks.getFileVersions,
      downloadVersion: vi.fn(),
    }))

    vi.doMock('@/api/diff', () => ({
      getDiffs: mocks.getDiffs,
    }))

    vi.doMock('@/utils/preview', () => ({
      buildAuthenticatedPreviewUrl: mocks.buildAuthenticatedPreviewUrl,
    }))

    DiffView = (await import('../DiffView.vue')).default
  })

  it('counts DOCX text, table, and image changes in the result header', async () => {
    const wrapper = mountDiffView()

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('7')
  })

  it('routes html files through the semantic diff API instead of zero-change preview fallback', async () => {
    mocks.getFileVersions.mockResolvedValueOnce({
      file_type: 'html',
      filename: 'landing.html',
      versions: [
        { id: 1, version: 1, created_at: '2026-06-01T00:00:00Z' },
        { id: 2, version: 2, created_at: '2026-06-02T00:00:00Z' },
      ],
    })
    mocks.getDiffs.mockResolvedValueOnce({
      diffs: [{
        summary: '修改 1 处文本，资源变化 1 处',
        diff_type: 'html',
        diff_data: {
          type: 'html_diff',
          text: [{ change_type: 'modified', tag: 'p', old_text: 'old', new_text: 'new' }],
          nodes: [],
          attributes: [],
          resources: [{ attribute: 'src', old_value: '/old.png', new_value: '/new.png' }],
          tables: [],
          metadata: { file_type: 'html' },
          status: 'completed',
          stats: {
            text_modified: 1,
            resources_changed: 1,
            total_changes: 2,
          },
          payload: {},
        },
      }],
    })

    const wrapper = mountDiffView()

    await flushPromises()
    await flushPromises()

    expect(mocks.getDiffs).toHaveBeenCalledWith('file-1', {
      old_version: 1,
      new_version: 2,
    })
    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenNthCalledWith(
      1,
      'file-1',
      1,
      'token-123',
      'html-diff-v1-old',
    )
    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenNthCalledWith(
      2,
      'file-1',
      2,
      'token-123',
      'html-diff-v2-new',
    )

    expect(wrapper.find('.html-semantic-stub').exists()).toBe(true)
    expect(wrapper.findAll('iframe.html-diff-frame')).toHaveLength(0)
  })
})
