import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ProjectDetail from '../ProjectDetail.vue'

const mocks = vi.hoisted(() => ({
  getProject: vi.fn(),
  getProjectFiles: vi.fn(),
  getPreviewStatuses: vi.fn(),
  clientGet: vi.fn(),
  clientPut: vi.fn(),
  buildAuthenticatedPreviewUrl: vi.fn(),
  buildPreviewSrcdoc: vi.fn((html) => html),
  shouldShowPreviewFrame: vi.fn(() => true),
  buildShareUrl: vi.fn(),
  isPreviewActiveStatus: vi.fn(() => false),
  mergeCreatedShareToken: vi.fn(({ project, files, shareTokensByResource }) => ({ project, files, shareTokensByResource })),
  normalizePreviewStatusRow: vi.fn((_file, row) => row || { status: 'missing' }),
  previewStatusLabel: vi.fn((status) => status || 'missing'),
  routerPush: vi.fn(),
  routerReplace: vi.fn(() => Promise.resolve()),
  route: {
    params: { id: 'project-1' },
    query: {},
    path: '/admin/projects/project-1',
    hash: '',
  },
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: { value: false },
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({
    push: mocks.routerPush,
    replace: mocks.routerReplace,
  }),
}))

vi.mock('@/api/project', () => ({
  getProject: mocks.getProject,
  getProjectFiles: mocks.getProjectFiles,
}))

vi.mock('@/api/file', () => ({
  deleteFile: vi.fn(),
  getPreviewStatuses: mocks.getPreviewStatuses,
  enqueuePreviewGeneration: vi.fn(),
  clearPreviewCache: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  default: {
    get: mocks.clientGet,
    post: vi.fn(),
    put: mocks.clientPut,
    delete: vi.fn(),
  },
}))

vi.mock('@/api/share', () => ({
  createShareToken: vi.fn(),
}))

vi.mock('@/utils/cover', () => ({
  resolveCoverUrl: vi.fn((value) => value || ''),
}))

vi.mock('@/utils', () => ({
  formatDate: vi.fn(() => '2026-06-16 12:00'),
  formatFileSize: vi.fn(() => '1 KB'),
  getFileTypeIcon: vi.fn(() => 'Document'),
  copyToClipboard: vi.fn(() => Promise.resolve()),
}))

vi.mock('@/utils/preview', () => ({
  buildAuthenticatedPreviewUrl: mocks.buildAuthenticatedPreviewUrl,
  buildPreviewSrcdoc: mocks.buildPreviewSrcdoc,
  shouldShowPreviewFrame: mocks.shouldShowPreviewFrame,
}))

vi.mock('@/utils/previewManagement', () => ({
  buildShareUrl: mocks.buildShareUrl,
  isPreviewActiveStatus: mocks.isPreviewActiveStatus,
  mergeCreatedShareToken: mocks.mergeCreatedShareToken,
  normalizePreviewStatusRow: mocks.normalizePreviewStatusRow,
  previewStatusLabel: mocks.previewStatusLabel,
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(),
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  ArrowLeft: { template: '<i />' },
  Upload: { template: '<i />' },
  Search: { template: '<i />' },
  View: { template: '<i />' },
  Sort: { template: '<i />' },
  Delete: { template: '<i />' },
  ArrowUp: { template: '<i />' },
  ArrowDown: { template: '<i />' },
  Document: { template: '<i />' },
  Download: { template: '<i />' },
  WarningFilled: { template: '<i />' },
  Loading: { template: '<i />' },
  Edit: { template: '<i />' },
  PriceTag: { template: '<i />' },
  Share: { template: '<i />' },
  RefreshRight: { template: '<i />' },
  MoreFilled: { template: '<i />' },
  Folder: { template: '<i />' },
  FolderOpened: { template: '<i />' },
  Plus: { template: '<i />' },
}))

const globalMountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      PageHeader: { template: '<div><slot name="actions" /></div>' },
      ElCard: { template: '<div><slot name="header" /><slot /></div>' },
      ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
      ElTag: { template: '<span><slot /></span>' },
      ElInput: {
        props: ['modelValue'],
        emits: ['update:modelValue', 'clear'],
        inheritAttrs: false,
        template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      },
      ElSelect: { template: '<div><slot /></div>' },
      ElOption: { template: '<option />' },
      ElTable: { template: '<div />' },
      ElTableColumn: { template: '<div />' },
      ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
      ElEmpty: { template: '<div><slot /></div>' },
      ElForm: { template: '<form><slot /></form>' },
      ElFormItem: { template: '<div><slot /></div>' },
      ElTooltip: { template: '<div><slot /></div>' },
      ElProgress: { template: '<div />' },
      ElIcon: { template: '<i><slot /></i>' },
      ElUpload: { template: '<div><slot /></div>' },
      ElInputNumber: { template: '<input />' },
      ElSwitch: { template: '<input type="checkbox" />' },
      ElDatePicker: { template: '<input />' },
      ElDropdown: { template: '<div><slot /><slot name="dropdown" /></div>' },
      ElDropdownMenu: { template: '<div><slot /></div>' },
      ElDropdownItem: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
      ElRadioGroup: { template: '<div><slot /></div>' },
      ElRadioButton: { template: '<button><slot /></button>' },
      FileListCards: { template: '<div />' },
    },
    directives: { loading: {} },
  },
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('ProjectDetail html preview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'token-123')
    mocks.getProject.mockResolvedValue({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [],
    })
    mocks.getProjectFiles.mockResolvedValue({ files: [] })
    mocks.getPreviewStatuses.mockResolvedValue({ files: [], summary: {} })
    mocks.clientPut.mockResolvedValue({})
    mocks.buildShareUrl.mockReturnValue('http://localhost/share/token')
    mocks.buildAuthenticatedPreviewUrl.mockImplementation((fileId, version, token, cacheKey) => (
      `/api/v1/files/${fileId}/preview?version=${version}&auth_token=${token}&_preview=${cacheKey}`
    ))
    mocks.clientGet.mockImplementation((url) => {
      if (url === '/tags' || url === '/categories' || url === '/files/file-html/versions') {
        return Promise.resolve([])
      }
      if (url === '/files/file-html/preview') {
        return Promise.resolve('<!DOCTYPE html><html><body><button>开始</button></body></html>')
      }
      return Promise.resolve({})
    })
  })

  it('uses direct authenticated iframe preview for html files instead of srcdoc sandbox fallback', async () => {
    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handlePreview = getExpose(wrapper, 'handlePreview')
    expect(typeof handlePreview).toBe('function')

    handlePreview({
      id: 'file-html',
      original_filename: 'demo.html',
      filename: 'demo.html',
      file_type: 'html',
      current_version: 1,
      updated_at: '2026-06-27T10:00:00Z',
    })
    await flushPromises()
    await flushPromises()

    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenCalledWith(
      'file-html',
      1,
      'token-123',
      'file-html-v1-open',
    )
    expect(
      mocks.clientGet.mock.calls.some(([url]) => url === '/files/file-html/preview'),
    ).toBe(false)

    expect(getExpose(wrapper, 'previewUrl')).toContain(
      '/api/v1/files/file-html/preview?version=1&auth_token=token-123&_preview=file-html-v1-open',
    )
    expect(getExpose(wrapper, 'previewHtml')).toBe('')
    expect(getExpose(wrapper, 'previewFrameSandbox')).toBe(null)

    const iframe = wrapper.find('iframe.preview-iframe')
    if (iframe.exists()) {
      expect(iframe.attributes('src')).toContain('/api/v1/files/file-html/preview?version=1&auth_token=token-123&_preview=file-html-v1-open')
      expect(iframe.attributes('srcdoc')).toBeUndefined()
      expect(iframe.attributes('sandbox')).not.toBe('allow-same-origin')
    }
  })

  it('disables admin iframe zoom for native html previews so embedded interactions remain clickable', async () => {
    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handlePreview = getExpose(wrapper, 'handlePreview')
    handlePreview({
      id: 'file-html',
      original_filename: 'interactive.html',
      filename: 'interactive.html',
      file_type: 'html',
      current_version: 1,
      updated_at: '2026-06-27T10:00:00Z',
    })
    await flushPromises()
    await flushPromises()

    expect(getExpose(wrapper, 'previewIsNativeHtml')).toBe(true)

    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ProjectDetail.vue'), 'utf-8')
    expect(source).toContain("'preview-iframe--native-html': previewIsNativeHtml")
    const htmlStyleStart = source.indexOf('.preview-iframe--native-html')
    const htmlStyleEnd = source.indexOf('.preview-video-container', htmlStyleStart)
    const htmlStyleBlock = source.slice(htmlStyleStart, htmlStyleEnd)

    expect(htmlStyleBlock).toContain('zoom: 1;')
  })
})
