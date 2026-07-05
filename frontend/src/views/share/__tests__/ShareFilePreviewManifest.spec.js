import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ShareFile from '../ShareFile.vue'

let mockedShareFileData
const mocks = vi.hoisted(() => ({
  downloadViaIframe: vi.fn(),
}))
const shareApiMocks = vi.hoisted(() => ({
  getShareFile: vi.fn(),
  getShareVersions: vi.fn(() => Promise.resolve({
    share: { allow_download: true },
    versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['bin'] }],
  })),
  unlockShareAccess: vi.fn(() => Promise.resolve({ unlocked: true })),
}))

const shareSessionMocks = vi.hoisted(() => ({
  unlock: vi.fn(() => Promise.resolve({ unlocked: true, grant_token: 'grant-1' })),
  release: vi.fn(() => Promise.resolve({ released: true })),
  heartbeat: vi.fn(() => Promise.resolve({ active: true })),
  withShareHeaders: vi.fn(() => ({
    'X-Share-Tab-Id': 'tab-a',
    'X-Share-Grant': 'grant-1',
  })),
}))

const publicAccessSessionMocks = vi.hoisted(() => ({
  unlock: vi.fn(() => Promise.resolve({ unlocked: true, grant_token: 'access-grant-1' })),
  release: vi.fn(() => Promise.resolve({ released: true })),
  heartbeat: vi.fn(() => Promise.resolve({ active: true })),
  withAccessHeaders: vi.fn(() => ({
    'X-Access-Tab-Id': 'tab-a',
    'X-Access-Grant': 'access-grant-1',
  })),
}))

const shareResourceTicketMocks = vi.hoisted(() => ({
  getShareResourceUrl: vi.fn(),
}))

const versionHistoryMocks = vi.hoisted(() => ({
  buildDiffByNewVersion: vi.fn(() => ({})),
  canCompareWithPreviousVersion: vi.fn(() => false),
  getVersionDiffStats: vi.fn(() => null),
  isLatestVersion: vi.fn(() => true),
  normalizeVersionHistory: vi.fn((versions) => versions),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { token: 'share-token', fileId: 'file-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/share', () => ({
  getShareFile: shareApiMocks.getShareFile,
  getShareVersions: shareApiMocks.getShareVersions,
  getShareDiffs: () => Promise.resolve({ diffs: [] }),
  unlockShareAccess: shareApiMocks.unlockShareAccess,
}))

vi.mock('@/composables/useShareSession', () => ({
  useShareSession: () => ({
    tabId: 'tab-a',
    grantToken: { value: 'grant-1' },
    unlock: shareSessionMocks.unlock,
    release: shareSessionMocks.release,
    heartbeat: shareSessionMocks.heartbeat,
    withShareHeaders: shareSessionMocks.withShareHeaders,
    isPasswordRequiredError: (err) => err?.response?.data?.detail === 'share_password_required',
    getUnlockErrorMessage: (err) => (
      err?.response?.data?.detail === 'share_password_invalid'
        ? '密码错误，请重试'
        : '解锁失败，请稍后再试'
    ),
  }),
}))

vi.mock('@/composables/usePublicAccessSession', () => ({
  usePublicAccessSession: () => ({
    tabId: 'tab-a',
    grantToken: { value: 'access-grant-1' },
    unlock: publicAccessSessionMocks.unlock,
    release: publicAccessSessionMocks.release,
    heartbeat: publicAccessSessionMocks.heartbeat,
    withAccessHeaders: publicAccessSessionMocks.withAccessHeaders,
    isResourcePasswordRequiredError: (err) => err?.response?.data?.detail === 'resource_password_required',
    getUnlockErrorMessage: (err) => (
      err?.response?.data?.detail === 'resource_password_invalid'
        ? '访问密码错误，请重试'
        : '资源解锁失败，请稍后重试'
    ),
  }),
}))

vi.mock('@/utils', () => ({
  formatDate: (value) => value || '',
  formatFileSize: (value) => `${value} B`,
  downloadViaIframe: mocks.downloadViaIframe,
}))

vi.mock('@/utils/versionHistory', () => ({
  buildDiffByNewVersion: versionHistoryMocks.buildDiffByNewVersion,
  canCompareWithPreviousVersion: versionHistoryMocks.canCompareWithPreviousVersion,
  getVersionDiffStats: versionHistoryMocks.getVersionDiffStats,
  isLatestVersion: versionHistoryMocks.isLatestVersion,
  normalizeVersionHistory: versionHistoryMocks.normalizeVersionHistory,
}))

vi.mock('@/utils/shareResourceTickets', () => ({
  getShareResourceUrl: shareResourceTicketMocks.getShareResourceUrl,
}))

const passthrough = (name, tag = 'div') =>
  defineComponent({
    name,
    inheritAttrs: false,
    props: ['disabled'],
    emits: ['click'],
    setup(props, { slots, attrs, emit }) {
      return () => h(
        tag,
        {
          class: [name, attrs.class],
          disabled: props.disabled || undefined,
          ...attrs,
          onClick: (event) => emit('click', event),
        },
        slots.default?.(),
      )
    },
  })

const ElCard = defineComponent({
  name: 'ElCard',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('div', { class: ['el-card', attrs.class] }, [slots.header?.(), slots.default?.()])
  },
})

const ElDropdown = defineComponent({
  name: 'ElDropdown',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('div', { class: ['ElDropdown', attrs.class] }, [slots.default?.(), slots.dropdown?.()])
  },
})

const globalConfig = {
  components: {
    ElCard,
    ElButton: passthrough('ElButton', 'button'),
    ElTag: passthrough('ElTag', 'span'),
    ElIcon: passthrough('ElIcon', 'span'),
    ElDropdown,
    ElDropdownMenu: passthrough('ElDropdownMenu'),
    ElDropdownItem: passthrough('ElDropdownItem'),
    ElEmpty: passthrough('ElEmpty'),
    ElSkeleton: passthrough('ElSkeleton'),
    ElResult: passthrough('ElResult'),
    ElTimeline: passthrough('ElTimeline'),
    ElTimelineItem: passthrough('ElTimelineItem'),
  },
}

describe('ShareFile version page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    shareApiMocks.getShareFile.mockImplementation(() => Promise.resolve(mockedShareFileData))
    shareApiMocks.getShareVersions.mockResolvedValue({
      share: { allow_download: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['bin'] }],
    })
    shareApiMocks.unlockShareAccess.mockResolvedValue({ unlocked: true })
    shareSessionMocks.unlock.mockResolvedValue({ unlocked: true, grant_token: 'grant-1' })
    shareSessionMocks.release.mockResolvedValue({ released: true })
    shareSessionMocks.heartbeat.mockResolvedValue({ active: true })
    shareSessionMocks.withShareHeaders.mockImplementation((headers = {}) => ({
      ...headers,
      'X-Share-Tab-Id': 'tab-a',
      'X-Share-Grant': 'grant-1',
    }))
    publicAccessSessionMocks.unlock.mockResolvedValue({ unlocked: true, grant_token: 'access-grant-1' })
    publicAccessSessionMocks.release.mockResolvedValue({ released: true })
    publicAccessSessionMocks.heartbeat.mockResolvedValue({ active: true })
    publicAccessSessionMocks.withAccessHeaders.mockImplementation((headers = {}) => ({
      ...headers,
      'X-Access-Tab-Id': 'tab-a',
      'X-Access-Grant': 'access-grant-1',
    }))
    versionHistoryMocks.buildDiffByNewVersion.mockReturnValue({})
    versionHistoryMocks.canCompareWithPreviousVersion.mockReturnValue(false)
    versionHistoryMocks.getVersionDiffStats.mockReturnValue(null)
    versionHistoryMocks.isLatestVersion.mockReturnValue(true)
    versionHistoryMocks.normalizeVersionHistory.mockImplementation((versions) => versions)
    shareResourceTicketMocks.getShareResourceUrl.mockImplementation(async ({
      token,
      kind,
      fileId,
      versionId,
      format,
    }) => {
      if (kind === 'download_converted') {
        return `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download/${format}?ticket=ticket-download-converted`
      }
      return `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download?ticket=ticket-download-original`
    })
    mockedShareFileData = {
      id: 'file-1',
      display_name: '压缩包',
      filename: 'opaque.bin',
      original_filename: 'opaque.bin',
      file_type: 'bin',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: { entry_count: 2, root_nodes: ['docs'] },
      preview_manifest: {
        type: 'archive_structure',
        status: 'ready',
        summary: { entry_count: 2, root_nodes: ['docs'] },
      },
    }
  })

  it('removes the preview card from the version page', async () => {
    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).not.toContain('文件预览')
    expect(wrapper.find('[data-testid="archive-structure-viewer"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="html-viewer-frame"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="video-player"]').exists()).toBe(false)
  })

  it('keeps version list visible for html files without embedding preview', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'HTML Report',
      filename: 'report.html',
      original_filename: 'report.html',
      file_type: 'html',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: {},
    }

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('版本历史')
    expect(wrapper.find('[data-testid="html-viewer-frame"]').exists()).toBe(false)
  })

  it('shows version history for video files without rendering the inline player', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Course Video',
      filename: 'lesson.mp4',
      original_filename: 'lesson.mp4',
      file_type: 'mp4',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: { duration_seconds: 12 },
      preview_manifest: {
        type: 'video_native',
        status: 'ready',
        primary_asset: {
          asset_type: 'poster',
          url: '/api/v1/share/share-token/files/file-1/preview-assets/poster-1',
        },
        poster_asset: {
          asset_type: 'poster',
          url: '/api/v1/share/share-token/files/file-1/preview-assets/poster-1',
        },
        summary: { duration_seconds: 12 },
      },
    }

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="video-player"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('版本历史')
  })

  it('renders diff and download actions as disabled grey buttons when share permissions close them', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Locked Spec',
      filename: 'locked.docx',
      original_filename: 'locked.docx',
      file_type: 'docx',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      download_formats: ['docx'],
      share: { allow_download: false, allow_diff: false, allow_versions: true },
      analysis_summary: {},
    }
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      share: { allow_download: false, allow_diff: false, allow_versions: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['docx'] }],
    })
    versionHistoryMocks.canCompareWithPreviousVersion.mockReturnValue(true)

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const downloadButton = buttons.find((button) => button.text().includes('禁止下载'))
    const diffButton = buttons.find((button) => button.text().includes('查看变更'))

    expect(downloadButton?.attributes('disabled')).toBeDefined()
    expect(diffButton?.attributes('disabled')).toBeDefined()
  })

  it('downloads the original file by default from the version page', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Course Video',
      filename: 'lesson.mp4',
      original_filename: 'lesson.mp4',
      file_type: 'mp4',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      download_formats: ['mp4'],
      share: { allow_download: true },
      analysis_summary: {},
    }
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      share: { allow_download: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['mp4'] }],
    })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const downloadButton = wrapper.find('[data-testid="share-file-download-original"]')
    expect(downloadButton.exists()).toBe(true)

    await downloadButton.trigger('click')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-1/versions/version-1/download?ticket=ticket-download-original',
    )
  })

  it('uses format-specific download on the version page when backend exposes multiple formats', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Spec',
      filename: 'spec.docx',
      original_filename: 'spec.docx',
      file_type: 'docx',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      download_formats: ['docx', 'pdf'],
      share: { allow_download: true },
      analysis_summary: {},
    }
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      share: { allow_download: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['docx', 'pdf'] }],
    })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    await vm.handleDownload({ id: 'version-1', download_formats: ['docx', 'pdf'] }, 'pdf')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-1/versions/version-1/download/pdf?ticket=ticket-download-converted',
    )
  })

  it('renders dropdown-style format choices on the version page for multi-format files', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Spec',
      filename: 'spec.docx',
      original_filename: 'spec.docx',
      file_type: 'docx',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      download_formats: ['docx', 'pdf'],
      share: { allow_download: true },
      analysis_summary: {},
    }
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      share: { allow_download: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['docx', 'pdf'] }],
    })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-file-download-original"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="选择下载格式"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('PDF')
  })


  it('keeps alternate downloads visible when the version payload is less complete than the file payload', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Legacy Spec',
      filename: 'legacy.doc',
      original_filename: 'legacy.doc',
      file_type: 'doc',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      download_formats: ['doc', 'pdf'],
      share: { allow_download: true },
      analysis_summary: {},
    }
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      share: { allow_download: true },
      versions: [{ id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['doc'] }],
    })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-file-download-original"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="选择下载格式"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('PDF')
  })

  it('prompts for password-protected version pages and retries after unlock', async () => {
    shareApiMocks.getShareFile
      .mockRejectedValueOnce({ response: { data: { detail: 'share_password_required' } } })
      .mockResolvedValueOnce({
        id: 'file-1',
        display_name: 'Unlocked Binary',
        filename: 'opaque.bin',
        original_filename: 'opaque.bin',
        file_type: 'bin',
        file_size: 1024,
        created_at: '2026-06-17T10:00:00Z',
        share: { allow_download: true },
        analysis_summary: {},
      })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(shareSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareFile).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Binary')
  })

  it('prompts for legacy public file passwords and retries after resource unlock', async () => {
    shareApiMocks.getShareFile
      .mockRejectedValueOnce({ response: { data: { detail: 'resource_password_required' } } })
      .mockResolvedValueOnce({
        id: 'file-1',
        display_name: 'Unlocked Binary',
        filename: 'opaque.bin',
        original_filename: 'opaque.bin',
        file_type: 'bin',
        file_size: 1024,
        created_at: '2026-06-17T10:00:00Z',
        share: { allow_download: true },
        analysis_summary: {},
      })

    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(publicAccessSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareFile).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Binary')
  })

})
