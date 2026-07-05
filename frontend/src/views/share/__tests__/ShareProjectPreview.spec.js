import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ShareProject from '../ShareProject.vue'

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  downloadViaIframe: vi.fn(),
  messageWarning: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { token: 'share-token' } }),
  useRouter: () => ({ push: mocks.routerPush }),
}))

const shareApiMocks = vi.hoisted(() => ({
  getShareProject: vi.fn(() => Promise.resolve({
    project: { name: 'Shared Project', description: '' },
    share: { allow_download: true },
    folders: [],
    files: [
      {
        id: 'file-1',
        display_name: 'Demo Video',
        original_filename: 'demo.mp4',
        filename: 'demo.mp4',
        folder_id: '',
        file_type: 'mp4',
        current_version: 1,
        updated_at: '2026-06-27T10:00:00Z',
        download_formats: ['mp4'],
        versions: [{ id: 'version-1' }],
      },
    ],
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

vi.mock('@/api/share', () => ({
  getShareProject: shareApiMocks.getShareProject,
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

vi.mock('element-plus', () => ({
  ElMessage: {
    warning: mocks.messageWarning,
  },
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: { value: false },
  }),
}))

vi.mock('@/utils', () => ({
  formatDate: (value) => value || '',
  getFileTypeIcon: () => 'Document',
  downloadViaIframe: mocks.downloadViaIframe,
}))

vi.mock('@/utils/shareProjectSearch', () => ({
  filterShareFiles: (items) => items,
}))

vi.mock('@/utils/shareResourceTickets', () => ({
  getShareResourceUrl: shareResourceTicketMocks.getShareResourceUrl,
}))

const passthrough = (name, tag = 'div') =>
  defineComponent({
    name,
    inheritAttrs: false,
    props: ['disabled', 'data'],
    emits: ['click'],
    setup(props, { slots, emit, attrs }) {
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

const ElTableColumn = defineComponent({
  name: 'ElTableColumn',
  props: ['prop', 'label'],
  setup() {
    return () => null
  },
})

const ElTable = defineComponent({
  name: 'ElTable',
  props: ['data'],
  setup(props, { slots, attrs }) {
    return () => {
      const columns = (slots.default?.() || []).filter((vnode) => vnode && vnode.type)
      return h(
        'div',
        { class: ['el-table', attrs.class] },
        (props.data || []).map((row, rowIndex) =>
          h(
            'div',
            { class: 'el-table__row', 'data-row': rowIndex },
            columns.map((column, columnIndex) => {
              const cellSlot = column.children?.default
              const content = cellSlot ? cellSlot({ row, $index: rowIndex }) : row[column.props?.prop] ?? ''
              return h('div', { class: 'el-table__cell', 'data-column': columnIndex }, content)
            }),
          ),
        ),
      )
    }
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
    ElTable,
    ElTableColumn,
    ElButton: passthrough('ElButton', 'button'),
    ElTag: passthrough('ElTag', 'span'),
    ElIcon: passthrough('ElIcon', 'span'),
    ElDropdown,
    ElDropdownMenu: passthrough('ElDropdownMenu'),
    ElDropdownItem: passthrough('ElDropdownItem'),
    ElTooltip: passthrough('ElTooltip'),
    ElEmpty: passthrough('ElEmpty'),
    ElSkeleton: passthrough('ElSkeleton'),
    ElResult: passthrough('ElResult'),
    ElInput: passthrough('ElInput', 'input'),
  },
}

describe('ShareProject preview action', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    shareApiMocks.getShareProject.mockResolvedValue({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-1',
          display_name: 'Demo Video',
          original_filename: 'demo.mp4',
          filename: 'demo.mp4',
          folder_id: '',
          file_type: 'mp4',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          download_formats: ['mp4'],
          versions: [{ id: 'version-1' }],
        },
      ],
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
    shareResourceTicketMocks.getShareResourceUrl.mockImplementation(async ({
      token,
      kind,
      fileId,
      versionId,
      folderId,
      format,
    }) => {
      if (kind === 'folder_download') {
        return `/api/v1/share/${token}/folders/${folderId}/download?ticket=ticket-folder-download`
      }
      if (kind === 'download_converted') {
        return `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download/${format}?ticket=ticket-download-converted`
      }
      return `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download?ticket=ticket-download-original`
    })
  })

  it('navigates to preview in the same tab by default', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const previewButton = wrapper.findAll('button').find((button) => button.text().includes('预览'))
    expect(previewButton).toBeTruthy()

    await previewButton.trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith('/s/share-token/preview/file-1')
    expect(openSpy).not.toHaveBeenCalled()

    openSpy.mockRestore()
  })

  it('downloads the original file by default from the file list', async () => {
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const downloadButton = wrapper.find('[data-testid="share-project-download-original"]')
    expect(downloadButton.exists()).toBe(true)

    await downloadButton.trigger('click')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-1/versions/version-1/download?ticket=ticket-download-original',
    )
  })

  it('downloads folder bundles from the unified resource list', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [{ id: 'folder-1', name: 'Contracts' }],
      files: [
        {
          id: 'file-root',
          display_name: 'Root PDF',
          original_filename: 'root.pdf',
          filename: 'root.pdf',
          folder_id: '',
          file_type: 'pdf',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          download_formats: ['pdf'],
          versions: [{ id: 'version-root' }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    expect(typeof vm.downloadFolderBundle).toBe('function')

    await vm.downloadFolderBundle({ id: 'folder-1', name: 'Contracts' })
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/folders/folder-1/download?ticket=ticket-folder-download',
    )
  })

  it('blocks folder download with the canonical warning copy when download is disabled', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: false },
      folders: [{ id: 'folder-1', name: 'Contracts' }],
      files: [
        {
          id: 'file-1',
          display_name: 'Read Only PDF',
          original_filename: 'readonly.pdf',
          filename: 'readonly.pdf',
          folder_id: '',
          file_type: 'pdf',
          current_version: 1,
          updated_at: '2026-06-28T10:00:00Z',
          download_formats: ['pdf'],
          versions: [{ id: 'version-1' }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('禁止下载')

    const vm = wrapper.vm.$?.setupState
    expect(typeof vm.downloadFolderBundle).toBe('function')

    await vm.downloadFolderBundle({ id: 'folder-1', name: 'Contracts' })
    await flushPromises()

    expect(mocks.messageWarning).toHaveBeenCalledWith('当前分享未开放下载')
    expect(mocks.downloadViaIframe).not.toHaveBeenCalled()
  })

  it('renders preview, version and diff actions as disabled grey buttons when share permissions close them', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: {
        allow_download: false,
        allow_preview: false,
        allow_diff: false,
        allow_versions: false,
      },
      folders: [],
      files: [
        {
          id: 'file-1',
          display_name: 'Locked Demo',
          original_filename: 'locked.mp4',
          filename: 'locked.mp4',
          folder_id: '',
          file_type: 'mp4',
          current_version: 1,
          updated_at: '2026-06-28T10:00:00Z',
          download_formats: ['mp4'],
          versions: [{ id: 'version-1' }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const previewButton = buttons.find((button) => button.text().includes('预览'))
    const versionButton = buttons.find((button) => button.text().includes('版本'))
    const diffButton = buttons.find((button) => button.text().includes('变更'))
    const downloadButton = buttons.find((button) => button.text().includes('禁止下载'))

    expect(previewButton?.attributes('disabled')).toBeDefined()
    expect(versionButton?.attributes('disabled')).toBeDefined()
    expect(diffButton?.attributes('disabled')).toBeDefined()
    expect(downloadButton?.attributes('disabled')).toBeDefined()
  })

  it('uses format-specific download when multiple formats are provided by backend', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-2',
          display_name: 'Project Spec',
          original_filename: 'spec.docx',
          filename: 'spec.docx',
          folder_id: '',
          file_type: 'docx',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          download_formats: ['docx', 'pdf'],
          versions: [{ id: 'version-2' }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    await vm.handleDownloadLatest({
      id: 'file-2',
      file_type: 'docx',
      download_formats: ['docx', 'pdf'],
      versions: [{ id: 'version-2' }],
    }, 'pdf')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-2/versions/version-2/download/pdf?ticket=ticket-download-converted',
    )
  })

  it('renders dropdown-style download selection for multi-format files', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-2',
          display_name: 'Project Spec',
          original_filename: 'spec.docx',
          filename: 'spec.docx',
          folder_id: '',
          file_type: 'docx',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          download_formats: ['docx', 'pdf'],
          versions: [{ id: 'version-2' }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-project-download-original"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="选择下载格式"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('PDF')
  })

  it('falls back to latest version download_formats when file-level formats are absent', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-3',
          display_name: 'Fallback Spec',
          original_filename: 'fallback.docx',
          filename: 'fallback.docx',
          folder_id: '',
          file_type: 'docx',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          versions: [{ id: 'version-3', download_formats: ['docx', 'pdf'] }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-project-download-original"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="选择下载格式"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('PDF')

    const vm = wrapper.vm.$?.setupState
    await vm.handleDownloadLatest({
      id: 'file-3',
      file_type: 'docx',
      versions: [{ id: 'version-3', download_formats: ['docx', 'pdf'] }],
    }, 'pdf')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-3/versions/version-3/download/pdf?ticket=ticket-download-converted',
    )
  })

  it('prefers the actual latest version when only that version exposes multi-format downloads', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-4',
          display_name: 'Versioned Spec',
          original_filename: 'versioned.docx',
          filename: 'versioned.docx',
          folder_id: '',
          file_type: 'docx',
          current_version: 3,
          updated_at: '2026-06-27T10:00:00Z',
          versions: [
            { id: 'version-1', version: 1, download_formats: ['docx'] },
            { id: 'version-3', version: 3, download_formats: ['docx', 'pdf'] },
          ],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-project-download-original"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('PDF 下载')

    const vm = wrapper.vm.$?.setupState
    await vm.handleDownloadLatest({
      id: 'file-4',
      file_type: 'docx',
      current_version: 3,
      versions: [
        { id: 'version-1', version: 1, download_formats: ['docx'] },
        { id: 'version-3', version: 3, download_formats: ['docx', 'pdf'] },
      ],
    }, 'pdf')
    await flushPromises()

    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-4/versions/version-3/download/pdf?ticket=ticket-download-converted',
    )
  })

  it('merges richer latest-version download formats when file-level formats are incomplete', async () => {
    shareApiMocks.getShareProject.mockResolvedValueOnce({
      project: { name: 'Shared Project', description: '' },
      share: { allow_download: true },
      folders: [],
      files: [
        {
          id: 'file-5',
          display_name: 'Legacy Spec',
          original_filename: 'legacy.doc',
          filename: 'legacy.doc',
          folder_id: '',
          file_type: 'doc',
          current_version: 1,
          updated_at: '2026-06-27T10:00:00Z',
          download_formats: ['doc'],
          versions: [{ id: 'version-5', version: 1, download_formats: ['doc', 'pdf'] }],
        },
      ],
    })

    const wrapper = mount(ShareProject, { global: globalConfig })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-project-download-original"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="选择下载格式"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('PDF')
  })

  it('wraps share mobile resource controls instead of forcing horizontal breadcrumb scrolling', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ShareProject.vue'), 'utf-8')
    const mobileStart = source.indexOf('@media (max-width: 767px)')
    const mobileBlock = source.slice(mobileStart)

    expect(mobileBlock).toContain('.resource-breadcrumb')
    expect(mobileBlock).toContain('flex-wrap: wrap;')
    expect(mobileBlock).toContain('white-space: normal;')
    expect(mobileBlock).not.toContain('overflow-x: auto;')
  })

  it('prompts for password-protected shares and retries after unlock', async () => {
    shareApiMocks.getShareProject
      .mockRejectedValueOnce({ response: { data: { detail: 'share_password_required' } } })
      .mockResolvedValueOnce({
        project: { name: 'Unlocked Project', description: 'Visible after unlock' },
        share: { allow_download: true },
        folders: [],
        files: [],
      })

    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(shareSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareProject).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Project')
  })

  it('prompts for legacy public resource passwords and retries after resource unlock', async () => {
    shareApiMocks.getShareProject
      .mockRejectedValueOnce({ response: { data: { detail: 'resource_password_required' } } })
      .mockResolvedValueOnce({
        project: { name: 'Unlocked Public Project', description: 'Visible after resource unlock' },
        share: { allow_download: true },
        folders: [],
        files: [],
      })

    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(publicAccessSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareProject).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Public Project')
  })

})
