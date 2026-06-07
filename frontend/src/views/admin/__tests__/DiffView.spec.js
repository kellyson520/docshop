import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DiffView from '../DiffView.vue'
import { getFileVersions } from '@/api/file'
import { getDiffs } from '@/api/diff'

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'project-1', fileId: 'file-1' }
  }),
  useRouter: () => ({
    push: vi.fn()
  })
}))

vi.mock('@/api/file', () => ({
  getFileVersions: vi.fn(),
  downloadVersion: vi.fn()
}))

vi.mock('@/api/diff', () => ({
  getDiffs: vi.fn()
}))

const stubs = {
  DiffSummary: { template: '<div class="summary-stub" />' },
  DocxDiffView: { template: '<div class="docx-stub" />', props: ['diffData'] },
  XlsxDiffView: { template: '<div class="xlsx-stub" />', props: ['diffData'] },
  PdfDiffView: { template: '<div class="pdf-stub" />', props: ['diffData'] },
  ElSelect: { template: '<div class="el-select"><slot /></div>', props: ['modelValue'] },
  ElOption: { template: '<span class="el-option" />', props: ['label', 'value'] }
}

describe('admin DiffView', () => {
  beforeEach(() => {
    getFileVersions.mockResolvedValue({
      file_type: 'docx',
      filename: 'demo.docx',
      versions: [
        { id: 1, version: 1, created_at: '2026-06-01T00:00:00Z' },
        { id: 2, version: 2, created_at: '2026-06-02T00:00:00Z' }
      ]
    })
    getDiffs.mockResolvedValue({
      diffs: [{
        summary: '新增 1 段；2 个表格变化；新增 1 张图片；删除 1 张图片；替换 1 张图片；尺寸调整 1 张图片',
        diff_type: 'docx_diff',
        diff_data: {
          text: [{ change_type: 'insert', new_text: '新增段落' }],
          tables: [{ table_index: 0 }, { table_index: 1 }],
          images: {
            added: [{ filename: 'a.png' }],
            deleted: [{ filename: 'b.png' }],
            replaced: [{ filename: 'c.png' }],
            resized: [{ filename: 'd.png' }]
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
            total_changes: 7
          }
        }
      }]
    })
  })

  it('counts DOCX text, table, and image changes in the result header', async () => {
    const wrapper = mount(DiffView, {
      global: {
        stubs,
        directives: { loading: {} }
      }
    })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('7 处变更')
  })
})
