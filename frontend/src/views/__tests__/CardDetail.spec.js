import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import CardDetail from '../CardDetail.vue'

const mocks = vi.hoisted(() => ({
  getDetail: vi.fn(),
  recordVisit: vi.fn(),
  downloadLatest: vi.fn(),
  downloadVersion: vi.fn(),
  getDiffs: vi.fn(),
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
  messageWarning: vi.fn(),
  routerPush: vi.fn(),
  route: {
    params: { id: 'card-1' },
    query: {},
    path: '/admin/cards/card-1',
    meta: {},
  },
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({
    push: mocks.routerPush,
  }),
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: false,
  }),
}))

vi.mock('@/api/card', () => ({
  cardApi: {
    getDetail: mocks.getDetail,
    recordVisit: mocks.recordVisit,
    downloadLatest: mocks.downloadLatest,
    downloadVersion: mocks.downloadVersion,
  },
}))

vi.mock('@/api/diff', () => ({
  getDiffs: mocks.getDiffs,
}))

vi.mock('@/utils/cover', () => ({
  resolveCoverUrl: vi.fn((value) => value || ''),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: mocks.messageSuccess,
    error: mocks.messageError,
    warning: mocks.messageWarning,
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  Document: { template: '<i />' },
  Files: { template: '<i />' },
  Clock: { template: '<i />' },
  Folder: { template: '<i />' },
  Download: { template: '<i />' },
  Sort: { template: '<i />' },
  Edit: { template: '<i />' },
  Share: { template: '<i />' },
  Unlock: { template: '<i />' },
  Lock: { template: '<i />' },
  View: { template: '<i />' },
  StarFilled: { template: '<i />' },
  Check: { template: '<i />' },
  Star: { template: '<i />' },
  EditPen: { template: '<i />' },
  HomeFilled: { template: '<i />' },
  Timer: { template: '<i />' },
  List: { template: '<i />' },
  CollectionTag: { template: '<i />' },
}))

vi.mock('@/components/compare/MultiVersionCompare.vue', () => ({
  default: { name: 'MultiVersionCompare', template: '<div />' },
}))

vi.mock('@/components/diff/DocxDiffView.vue', () => ({
  default: { name: 'DocxDiffView', props: ['diffData'], template: '<div class="docx-diff-view" />' },
}))

vi.mock('@/components/diff/XlsxDiffView.vue', () => ({
  default: { name: 'XlsxDiffView', template: '<div />' },
}))

vi.mock('@/components/diff/PdfDiffView.vue', () => ({
  default: { name: 'PdfDiffView', template: '<div />' },
}))

vi.mock('@/components/diff/MediaDiffView.vue', () => ({
  default: { name: 'MediaDiffView', props: ['payload', 'summary'], template: '<div class="media-diff-view" />' },
}))

vi.mock('@/components/diff/ArchiveDiffView.vue', () => ({
  default: { name: 'ArchiveDiffView', props: ['payload', 'summary'], template: '<div class="archive-diff-view" />' },
}))

const globalMountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      ElSkeleton: { template: '<div />' },
      ElTimeline: { template: '<div><slot /></div>' },
      ElTimelineItem: { template: '<div><slot /></div>' },
      ElCard: { template: '<div><slot /></div>' },
      ElTag: { template: '<span><slot /></span>' },
      ElIcon: { template: '<i><slot /></i>' },
      ElButton: {
        props: ['disabled', 'loading'],
        emits: ['click'],
        template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
      },
      ElTable: { template: '<div><slot /></div>' },
      ElTableColumn: { template: '<div><slot /></div>' },
      ElDialog: { template: '<div><slot /></div>' },
      ElEmpty: { template: '<div><slot /></div>' },
      ElResult: { template: '<div><slot name="extra" /></div>' },
      ElRadioGroup: { template: '<div><slot /></div>' },
      ElRadioButton: { template: '<div><slot /></div>' },
    },
  },
}

function getSetupValue(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('CardDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getDetail.mockResolvedValue({
      id: 'card-1',
      display_name: '示例文档',
      filename: 'demo.docx',
      file_type: 'docx',
      cover_image: '',
      description: '',
      is_public: false,
      versions: [
        {
          id: 'ver-2',
          version: 2,
          created_at: '2026-06-16T10:00:00Z',
          changelog: '更新',
          file_size: 200,
          previous_version_id: 'ver-1',
        },
        {
          id: 'ver-1',
          version: 1,
          created_at: '2026-06-15T10:00:00Z',
          changelog: '初版',
          file_size: 100,
          previous_version_id: null,
        },
      ],
    })
    mocks.recordVisit.mockResolvedValue({})
  })

  it('uses diff API for single-version change view and parses diff_data', async () => {
    mocks.getDiffs.mockResolvedValue({
      diffs: [
        {
          id: 'diff-1',
          diff_data: JSON.stringify({
            type: 'docx_diff',
            summary: 'changed',
            stats: { paragraphs_modified: 1 },
          }),
        },
      ],
    })

    const wrapper = shallowMount(CardDetail, globalMountOptions)
    await flushPromises()

    const viewDiff = getSetupValue(wrapper, 'viewDiff')
    await viewDiff({
      id: 'ver-2',
      version: 2,
      previous_version_id: 'ver-1',
    })
    await flushPromises()

    expect(mocks.getDiffs).toHaveBeenCalledWith('card-1', {
      old_version: 'ver-1',
      new_version: 'ver-2',
    })
    expect(getSetupValue(wrapper, 'showDiff')).toBe(true)
    expect(getSetupValue(wrapper, 'diffData')).toEqual({
      type: 'docx_diff',
      summary: 'changed',
      stats: { paragraphs_modified: 1 },
    })
  })

  it('shows error and closes dialog when no matching diff exists', async () => {
    mocks.getDiffs.mockResolvedValue({ diffs: [] })

    const wrapper = shallowMount(CardDetail, globalMountOptions)
    await flushPromises()

    const viewDiff = getSetupValue(wrapper, 'viewDiff')
    await viewDiff({
      id: 'ver-2',
      version: 2,
      previous_version_id: 'ver-1',
    })
    await flushPromises()

    expect(mocks.messageError).toHaveBeenCalledWith(expect.stringContaining('未找到对应版本差异'))
    expect(getSetupValue(wrapper, 'showDiff')).toBe(false)
  })

  it('renders media diff view when diff type is media', async () => {
    mocks.getDetail.mockResolvedValueOnce({
      id: 'card-1',
      display_name: '演示视频',
      filename: 'demo.mp4',
      file_type: 'mp4',
      cover_image: '',
      description: '',
      is_public: false,
      versions: [
        {
          id: 'ver-2',
          version: 2,
          created_at: '2026-06-16T10:00:00Z',
          changelog: '更新画面',
          file_size: 200,
          previous_version_id: 'ver-1',
        },
        {
          id: 'ver-1',
          version: 1,
          created_at: '2026-06-15T10:00:00Z',
          changelog: '初版',
          file_size: 100,
          previous_version_id: null,
        },
      ],
    })
    mocks.getDiffs.mockResolvedValueOnce({
      diffs: [
        {
          id: 'diff-media-1',
          diff_type: 'media',
          diff_data: JSON.stringify({
            diff_type: 'media',
            payload: {
              left: { preview_url: '/left.mp4' },
              right: { preview_url: '/right.mp4' },
            },
            summary: { duration_delta_seconds: 12 },
          }),
        },
      ],
    })

    const wrapper = shallowMount(CardDetail, globalMountOptions)
    await flushPromises()

    const viewDiff = getSetupValue(wrapper, 'viewDiff')
    await viewDiff({
      id: 'ver-2',
      version: 2,
      previous_version_id: 'ver-1',
    })
    await flushPromises()

    expect(wrapper.findComponent({ name: 'MediaDiffView' }).exists()).toBe(true)
  })

  it('renders archive diff view when diff type is structure', async () => {
    mocks.getDetail.mockResolvedValueOnce({
      id: 'card-1',
      display_name: '演示压缩包',
      filename: 'demo.zip',
      file_type: 'zip',
      cover_image: '',
      description: '',
      is_public: false,
      versions: [
        {
          id: 'ver-2',
          version: 2,
          created_at: '2026-06-16T10:00:00Z',
          changelog: '新增目录',
          file_size: 200,
          previous_version_id: 'ver-1',
        },
        {
          id: 'ver-1',
          version: 1,
          created_at: '2026-06-15T10:00:00Z',
          changelog: '初版',
          file_size: 100,
          previous_version_id: null,
        },
      ],
    })
    mocks.getDiffs.mockResolvedValueOnce({
      diffs: [
        {
          id: 'diff-archive-1',
          diff_type: 'structure',
          diff_data: JSON.stringify({
            diff_type: 'structure',
            payload: {
              added_paths: ['docs/new.md'],
              removed_paths: [],
            },
            summary: { files_added: 1, files_removed: 0 },
          }),
        },
      ],
    })

    const wrapper = shallowMount(CardDetail, globalMountOptions)
    await flushPromises()

    const viewDiff = getSetupValue(wrapper, 'viewDiff')
    await viewDiff({
      id: 'ver-2',
      version: 2,
      previous_version_id: 'ver-1',
    })
    await flushPromises()

    expect(wrapper.findComponent({ name: 'ArchiveDiffView' }).exists()).toBe(true)
  })

})
