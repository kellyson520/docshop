import fs from 'node:fs'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, shallowMount, flushPromises } from '@vue/test-utils'
import ProjectDetail from '../ProjectDetail.vue'

const mocks = vi.hoisted(() => ({
  getProject: vi.fn(),
  getProjectFiles: vi.fn(),
  getProjectFolders: vi.fn(),
  getPreviewStatuses: vi.fn(),
  clientGet: vi.fn(),
  clientPut: vi.fn(),
  createShareToken: vi.fn(),
  listShareTokens: vi.fn(),
  updateShareToken: vi.fn(),
  listAccessGroups: vi.fn(),
  getResourceAccessPolicy: vi.fn(),
  updateResourceAccessPolicy: vi.fn(),
  buildAuthenticatedPreviewUrl: vi.fn(),
  buildPreviewSrcdoc: vi.fn((html) => html),
  shouldShowPreviewFrame: vi.fn(() => true),
  buildShareUrl: vi.fn(),
  indexLatestShareTokensByResource: vi.fn(),
  isPreviewActiveStatus: vi.fn(),
  mergeCreatedShareToken: vi.fn(),
  normalizePreviewStatusRow: vi.fn(),
  previewStatusLabel: vi.fn(),
  shareResourceKey: vi.fn(),
  confirm: vi.fn(),
  alert: vi.fn(),
  messageError: vi.fn(),
  messageSuccess: vi.fn(),
  messageInfo: vi.fn(),
  routerPush: vi.fn(),
  routerReplace: vi.fn(() => Promise.resolve()),
  consoleWarn: vi.fn(),
  responsiveState: {
    isMobile: false,
  },
  route: {
    params: { id: 'project-1' },
    query: {},
    path: '/admin/projects/project-1',
    hash: '',
  },
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: { value: mocks.responsiveState.isMobile },
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
  getProjectFolders: mocks.getProjectFolders,
  createProjectFolder: vi.fn(),
  renameProjectFolder: vi.fn(),
  deleteProjectFolder: vi.fn(),
  moveProjectFileToFolder: vi.fn(),
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
  createShareToken: mocks.createShareToken,
  listShareTokens: mocks.listShareTokens,
  updateShareToken: mocks.updateShareToken,
}))

vi.mock('@/api/accessControl', () => ({
  listAccessGroups: mocks.listAccessGroups,
  getResourceAccessPolicy: mocks.getResourceAccessPolicy,
  updateResourceAccessPolicy: mocks.updateResourceAccessPolicy,
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
  indexLatestShareTokensByResource: mocks.indexLatestShareTokensByResource,
  isPreviewActiveStatus: mocks.isPreviewActiveStatus,
  mergeCreatedShareToken: mocks.mergeCreatedShareToken,
  normalizePreviewStatusRow: mocks.normalizePreviewStatusRow,
  previewStatusLabel: mocks.previewStatusLabel,
  shareResourceKey: mocks.shareResourceKey,
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    error: mocks.messageError,
    success: mocks.messageSuccess,
    info: mocks.messageInfo,
  },
  ElMessageBox: {
    confirm: mocks.confirm,
    alert: mocks.alert,
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
  Lock: { template: '<i />' },
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
    },
    directives: { loading: {} },
  },
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('ProjectDetail preview update reminder', () => {
  let warnSpy

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'token-123')
    warnSpy = vi.spyOn(console, 'warn').mockImplementation((...args) => {
      mocks.consoleWarn(...args)
    })

    mocks.getProject.mockResolvedValue({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [],
    })
    mocks.getProjectFiles.mockResolvedValue({ files: [] })
    mocks.getProjectFolders.mockResolvedValue({ folders: [] })
    mocks.getPreviewStatuses.mockResolvedValue({ files: [], summary: {} })
    mocks.clientPut.mockResolvedValue({})
    mocks.buildShareUrl.mockImplementation(() => 'http://localhost/share/token')
    mocks.shareResourceKey.mockImplementation((resourceType, resourceId) => `${resourceType || 'project'}:${resourceId || ''}`)
    mocks.indexLatestShareTokensByResource.mockImplementation((items = []) => items.reduce((accumulator, token) => {
      const key = `${token?.resource_type || 'project'}:${token?.resource_id || ''}`
      const current = accumulator[key]
      const currentRecency = String(current?.updated_at || current?.created_at || '')
      const nextRecency = String(token?.updated_at || token?.created_at || '')
      if (!current || nextRecency >= currentRecency) {
        accumulator[key] = token
      }
      return accumulator
    }, {}))
    mocks.isPreviewActiveStatus.mockImplementation((status) => (
      ['queued', 'pdf_generating', 'pdf_ready', 'images_generating'].includes(status)
    ))
    mocks.mergeCreatedShareToken.mockImplementation(({ project, files, shareTokensByResource }) => ({
      project,
      files,
      shareTokensByResource,
    }))
    mocks.normalizePreviewStatusRow.mockImplementation((_file, row) => row || { status: 'missing' })
    mocks.previewStatusLabel.mockImplementation((status) => status || 'missing')
    mocks.buildAuthenticatedPreviewUrl.mockImplementation((fileId, version, token, cacheKey) => (
      `/api/v1/files/${fileId}/preview?version=${version}&token=${token}&cache=${cacheKey}`
    ))
    mocks.confirm.mockResolvedValue(undefined)
    mocks.listShareTokens.mockResolvedValue({ items: [] })
    mocks.updateShareToken.mockResolvedValue({})
    mocks.listAccessGroups.mockResolvedValue({
      items: [
        { id: 'group-legal', code: 'legal', name: 'Legal Team', is_active: true },
      ],
    })
    mocks.getResourceAccessPolicy.mockResolvedValue({
      visibility: 'public',
      allow_preview: true,
      allow_download: true,
      allow_diff: true,
      allow_versions: true,
      has_password: false,
      password_hint: '',
      group_codes: [],
    })
    mocks.updateResourceAccessPolicy.mockResolvedValue({})
    mocks.clientGet.mockImplementation((url, options = {}) => {
      if (url === '/files/file-1/preview') {
        return Promise.resolve(`PDF_BINARY_V${options?.params?.version || 'unknown'}`)
      }
      if (url === '/files/file-1') {
        return Promise.resolve({
          id: 'file-1',
          display_name: '合同.pdf',
          description: '',
          category_id: null,
          tags: [],
          cover_image: '',
        })
      }
      if (url === '/files/file-1/versions') {
        return Promise.resolve({
          versions: [
            { id: 'ver-4', version: 4 },
            { id: 'ver-2', version: 2 },
            { id: 'ver-1', version: 1 },
          ],
        })
      }
      if (url === '/tags' || url === '/categories') {
        return Promise.resolve([])
      }
      return Promise.resolve({})
    })
  })

  afterEach(() => {
    localStorage.clear()
    warnSpy?.mockRestore()
  })

  it('prompts viewers when a newer preview version is detected and reloads latest version after confirm', async () => {
    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const file = {
      id: 'file-1',
      original_filename: 'demo.pdf',
      filename: 'demo.pdf',
      file_type: 'pdf',
      current_version: 2,
      updated_at: '2026-06-16T10:00:00Z',
    }

    const handlePreview = getExpose(wrapper, 'handlePreview')
    const checkPreviewVersionUpdate = getExpose(wrapper, 'checkPreviewVersionUpdate')

    expect(typeof handlePreview).toBe('function')
    expect(typeof checkPreviewVersionUpdate).toBe('function')

    handlePreview(file)
    await flushPromises()

    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenLastCalledWith(
      'file-1',
      2,
      'token-123',
      'file-1-v2-open',
    )

    await checkPreviewVersionUpdate()
    await flushPromises()

    expect(mocks.confirm).toHaveBeenCalledTimes(1)
    expect(String(mocks.confirm.mock.calls[0][0])).toContain('v2')
    expect(String(mocks.confirm.mock.calls[0][0])).toContain('v4')
    expect(getExpose(wrapper, 'previewVersion')).toBe(4)
    expect(getExpose(wrapper, 'previewCacheKey')).toBe('file-1-v4-ver-4')
    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenLastCalledWith(
      'file-1',
      4,
      'token-123',
      'file-1-v4-ver-4',
    )
  })

  it('reloads preview when the latest version is rebuilt with a new refresh token', async () => {
    mocks.clientGet.mockImplementation((url, options = {}) => {
      if (url === '/files/file-1/preview') {
        return Promise.resolve(`PDF_BINARY_V${options?.params?.version || 'unknown'}`)
      }
      if (url === '/files/file-1/versions') {
        return Promise.resolve({
          versions: [
            { id: 'ver-2', version: 2, preview_refresh_token: 'refresh-token-v2b' },
            { id: 'ver-1', version: 1, preview_refresh_token: 'refresh-token-v1' },
          ],
        })
      }
      if (url === '/tags' || url === '/categories') {
        return Promise.resolve([])
      }
      return Promise.resolve({})
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const file = {
      id: 'file-1',
      original_filename: 'demo.pdf',
      filename: 'demo.pdf',
      file_type: 'pdf',
      current_version: 2,
      updated_at: '2026-06-16T10:00:00Z',
    }

    const handlePreview = getExpose(wrapper, 'handlePreview')
    const checkPreviewVersionUpdate = getExpose(wrapper, 'checkPreviewVersionUpdate')

    handlePreview(file)
    await flushPromises()

    expect(getExpose(wrapper, 'previewVersion')).toBe(2)
    expect(getExpose(wrapper, 'previewVersionRefreshToken')).toBe('')

    mocks.buildAuthenticatedPreviewUrl.mockClear()

    await checkPreviewVersionUpdate()
    await flushPromises()

    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(getExpose(wrapper, 'previewVersion')).toBe(2)
    expect(getExpose(wrapper, 'previewCacheKey')).toBe('file-1-v2-refresh-token-v2b')
    expect(getExpose(wrapper, 'previewVersionRefreshToken')).toBe('refresh-token-v2b')
    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenLastCalledWith(
      'file-1',
      2,
      'token-123',
      'file-1-v2-refresh-token-v2b',
    )
  })

  it('does not emit undefined handler warnings and tolerates missing original_filename in search', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-fallback',
          filename: 'fallback-name.docx',
          display_name: 'Fallback Name',
          file_type: 'docx',
          current_version: 1,
          tags: [],
        },
      ],
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const setupState = wrapper.vm.$?.setupState || {}
    setupState.fileSearchQuery = 'fallback'
    await wrapper.vm.$nextTick()

    const filteredFiles = getExpose(wrapper, 'filteredFiles')
    const normalizedFilteredFiles = Array.isArray(filteredFiles)
      ? filteredFiles
      : (filteredFiles?.value || [])

    expect(normalizedFilteredFiles).toHaveLength(1)

    const warnMessages = mocks.consoleWarn.mock.calls
      .flatMap((call) => call.map((item) => String(item)))
      .join('\n')

    expect(warnMessages).not.toContain('fetchCategoriesTags')
    expect(warnMessages).not.toContain('saveCategoryTags')
    expect(warnMessages).not.toContain('Failed setting prop "size"')
  })

  it('loads keyword search results from backend and keeps backend ranking before local filters', async () => {
    mocks.getProjectFiles.mockResolvedValueOnce({
      files: [
        {
          id: 'tag-match',
          filename: 'policy.pdf',
          display_name: '制度说明',
          file_type: 'pdf',
          current_version: 1,
          tags: [{ id: 'budget-tag', name: 'budget' }],
        },
        {
          id: 'name-match',
          filename: 'budget-summary.docx',
          display_name: 'Budget Summary',
          file_type: 'docx',
          current_version: 1,
          tags: [],
        },
      ],
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const setupState = wrapper.vm.$?.setupState || {}
    setupState.fileSearchQuery = 'budget'

    const searchProjectFiles = getExpose(wrapper, 'searchProjectFiles')
    expect(typeof searchProjectFiles).toBe('function')
    await searchProjectFiles()
    await flushPromises()

    expect(mocks.getProjectFiles).toHaveBeenCalledWith('project-1', { keyword: 'budget' })

    const filteredFiles = getExpose(wrapper, 'filteredFiles')
    const normalizedFilteredFiles = Array.isArray(filteredFiles)
      ? filteredFiles
      : (filteredFiles?.value || [])
    expect(normalizedFilteredFiles.map((file) => file.id)).toEqual(['tag-match', 'name-match'])

    setupState.fileTypeFilter = 'pdf'
    await wrapper.vm.$nextTick()
    const filteredPdfFiles = getExpose(wrapper, 'filteredFiles')
    const normalizedPdfFiles = Array.isArray(filteredPdfFiles)
      ? filteredPdfFiles
      : (filteredPdfFiles?.value || [])
    expect(normalizedPdfFiles.map((file) => file.id)).toEqual(['tag-match'])
  })

  it('refreshes searched file list after saving file settings so edited display name is visible', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-edit',
          filename: 'old-name.docx',
          display_name: '旧显示名',
          description: '',
          file_type: 'docx',
          current_version: 1,
          tags: [],
        },
      ],
    })
    mocks.getProjectFiles.mockResolvedValueOnce({
      files: [
        {
          id: 'file-edit',
          filename: 'old-name.docx',
          display_name: '新显示名',
          description: '新说明',
          file_type: 'docx',
          current_version: 1,
          tags: [],
        },
      ],
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const setupState = wrapper.vm.$?.setupState || {}
    setupState.fileSearchQuery = '新显示名'

    const openFileEditDialog = getExpose(wrapper, 'openFileEditDialog')
    const saveFileEdit = getExpose(wrapper, 'saveFileEdit')
    const files = getExpose(wrapper, 'files')
    openFileEditDialog(files[0])
    setupState.editForm = {
      display_name: '新显示名',
      description: '新说明',
      category_id: null,
      tag_ids: [],
      cover_image: '',
    }

    await saveFileEdit()
    await flushPromises()

    expect(mocks.clientPut).toHaveBeenCalledWith('/cards/file-edit/info', {
      display_name: '新显示名',
      description: '新说明',
    })
    expect(mocks.getProjectFiles).toHaveBeenCalledWith('project-1', { keyword: '新显示名' })
    expect(getExpose(wrapper, 'getFileDisplayName')(getExpose(wrapper, 'files')[0])).toBe('新显示名')
  })

  it('loads file public-browse controls and saves merged access payload from file settings', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      is_public: true,
      files: [
        {
          id: 'file-1',
          filename: 'contract.pdf',
          original_filename: 'contract.pdf',
          display_name: '合同.pdf',
          description: '',
          file_type: 'pdf',
          current_version: 1,
          tags: [],
        },
      ],
    })
    mocks.getResourceAccessPolicy.mockResolvedValueOnce({
      visibility: 'password_required',
      allow_preview: true,
      allow_download: false,
      allow_diff: false,
      allow_versions: true,
      has_password: true,
      password_hint: 'file code',
      group_codes: [],
    })
    mocks.clientGet.mockImplementation((url) => {
      if (url === '/files/file-1') {
        return Promise.resolve({
          id: 'file-1',
          display_name: '合同.pdf',
          description: '',
          category_id: null,
          tags: [],
          cover_image: '',
        })
      }
      if (url === '/files/file-1/versions') {
        return Promise.resolve({ versions: [{ id: 'ver-1', version: 1 }] })
      }
      if (url === '/tags' || url === '/categories') {
        return Promise.resolve([])
      }
      return Promise.resolve({})
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const file = getExpose(wrapper, 'files')[0]
    getExpose(wrapper, 'openFileEditDialog')(file)
    await getExpose(wrapper, 'loadFileEditData')()
    await flushPromises()

    expect(getExpose(wrapper, 'fileAccessForm')).toMatchObject({
      visibility: 'password_required',
      allow_preview: true,
      allow_download: false,
      allow_diff: false,
      allow_versions: true,
      has_password: true,
      password_hint: 'file code',
    })

    const fileAccessForm = getExpose(wrapper, 'fileAccessForm')
    fileAccessForm.visibility = 'groups_required'
    fileAccessForm.allow_preview = false
    fileAccessForm.allow_download = false
    fileAccessForm.allow_diff = true
    fileAccessForm.allow_versions = false
    fileAccessForm.password = ''
    fileAccessForm.clear_password = true
    fileAccessForm.password_hint = 'group only'
    fileAccessForm.group_codes = ['legal']

    await getExpose(wrapper, 'saveFileEdit')()
    await flushPromises()

    expect(mocks.updateResourceAccessPolicy).toHaveBeenCalledWith('file', 'file-1', {
      visibility: 'groups_required',
      allow_preview: false,
      allow_download: false,
      allow_diff: true,
      allow_versions: false,
      clear_password: true,
      password_hint: 'group only',
      group_codes: ['legal'],
    })
  })

  it('opens project public-browse dialog and saves project policy', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      is_public: true,
      files: [],
    })
    mocks.getResourceAccessPolicy.mockResolvedValueOnce({
      visibility: 'public',
      allow_preview: true,
      allow_download: true,
      allow_diff: true,
      allow_versions: true,
      has_password: false,
      password_hint: '',
      group_codes: [],
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    await getExpose(wrapper, 'openProjectAccessDialog')()
    await flushPromises()

    expect(getExpose(wrapper, 'projectAccessVisible')).toBe(true)
    expect(getExpose(wrapper, 'projectAccessForm')).toMatchObject({
      visibility: 'public',
      allow_preview: true,
      allow_download: true,
      allow_diff: true,
      allow_versions: true,
    })

    const projectAccessForm = getExpose(wrapper, 'projectAccessForm')
    projectAccessForm.visibility = 'groups_required'
    projectAccessForm.allow_preview = false
    projectAccessForm.allow_download = false
    projectAccessForm.allow_diff = false
    projectAccessForm.allow_versions = true
    projectAccessForm.password_hint = 'team only'
    projectAccessForm.group_codes = ['legal']

    await getExpose(wrapper, 'saveProjectAccessPolicy')()
    await flushPromises()

    expect(mocks.updateResourceAccessPolicy).toHaveBeenCalledWith('project', 'project-1', {
      visibility: 'groups_required',
      allow_preview: false,
      allow_download: false,
      allow_diff: false,
      allow_versions: true,
      password_hint: 'team only',
      group_codes: ['legal'],
    })
  })

  it('uses a search-specific empty state after keyword search returns no files', async () => {
    mocks.getProjectFiles.mockResolvedValueOnce({ files: [] })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const setupState = wrapper.vm.$?.setupState || {}
    setupState.fileSearchQuery = 'not-found'
    await getExpose(wrapper, 'searchProjectFiles')()
    await flushPromises()

    expect(getExpose(wrapper, 'fileEmptyDescription')).toBe('没有匹配文件，换个关键词试试')
  })

  it('filters file list by preview problem status without extra backend calls', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        { id: 'ready-file', filename: 'ready.pdf', file_type: 'pdf', current_version: 1, tags: [] },
        { id: 'failed-file', filename: 'failed.docx', file_type: 'docx', current_version: 1, tags: [] },
        { id: 'interrupted-file', filename: 'broken.doc', file_type: 'doc', current_version: 1, tags: [] },
      ],
    })
    mocks.getPreviewStatuses.mockResolvedValueOnce({
      files: [
        { file_id: 'ready-file', status: 'ready' },
        { file_id: 'failed-file', status: 'failed' },
        { file_id: 'interrupted-file', status: 'interrupted' },
      ],
      summary: {},
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const setupState = wrapper.vm.$?.setupState || {}
    setupState.previewStatusFilter = 'problem'
    await wrapper.vm.$nextTick()

    const filteredFiles = getExpose(wrapper, 'filteredFiles')
    const normalizedFilteredFiles = Array.isArray(filteredFiles)
      ? filteredFiles
      : (filteredFiles?.value || [])

    expect(normalizedFilteredFiles.map((file) => file.id)).toEqual(['failed-file', 'interrupted-file'])
    expect(mocks.getProjectFiles).not.toHaveBeenCalled()
  })

  it('uses edited display_name as the visible file name and falls back to original filename', async () => {
    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const getFileDisplayName = getExpose(wrapper, 'getFileDisplayName')
    expect(typeof getFileDisplayName).toBe('function')

    expect(getFileDisplayName({
      original_filename: 'original.docx',
      filename: 'original.docx',
      display_name: '对外显示名称',
    })).toBe('对外显示名称')

    expect(getFileDisplayName({
      original_filename: 'original.docx',
      filename: 'original.docx',
      display_name: '',
    })).toBe('original.docx')
  })



  it('renders compact action labels without mojibake placeholders', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')
    const start = source.indexOf('action-buttons action-buttons-compact')
    const end = source.indexOf('</el-table-column>', start)
    const actionSource = source.slice(start, end)

    expect(actionSource).toContain('\u9884\u89c8')
    expect(actionSource).toContain('\u5206\u4eab')
    expect(actionSource).toContain('\u8bbe\u7f6e')
    expect(actionSource).toContain('\u66f4\u591a')
    expect(actionSource).toContain('Diff \u5bf9\u6bd4')
    expect(actionSource).not.toContain('??')
  })

  it('routes compact file action menu commands to the original handlers', async () => {
    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handleFileRowAction = getExpose(wrapper, 'handleFileRowAction')
    expect(typeof handleFileRowAction).toBe('function')

    const file = {
      id: 'file-menu',
      original_filename: 'menu.docx',
      filename: 'menu.docx',
      file_type: 'docx',
      current_version: 1,
    }

    handleFileRowAction('diff', file)
    expect(mocks.routerPush).toHaveBeenCalledWith('/admin/projects/project-1/diff/file-menu')

    handleFileRowAction('new-version', file)
    expect(mocks.routerPush).toHaveBeenCalledWith({
      path: '/admin/projects/project-1/upload',
      query: { fileId: 'file-menu' },
  })
})

describe('ProjectDetail share access menu labels', () => {
  it('renders readable share-access labels in both desktop and mobile dropdown menus', async () => {
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ProjectDetail.vue'), 'utf-8')
    const matches = source.match(/command="share-access"[\s\S]{0,120}安全分享/g) || []

    expect(matches).toHaveLength(2)
    expect(source).not.toContain('瀹夊叏鍒嗕韩')
  })
})

  it('adds a secure-share command to both desktop and mobile file action menus', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source.match(/command="share-access"/g)).toHaveLength(2)
  })

  it('opens file secure share from the more menu with override access defaults', async () => {
    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handleFileRowAction = getExpose(wrapper, 'handleFileRowAction')
    expect(typeof handleFileRowAction).toBe('function')

    const file = {
      id: 'file-secure-share',
      original_filename: 'restricted.docx',
      filename: 'restricted.docx',
      file_type: 'docx',
      current_version: 1,
    }

    handleFileRowAction('share-access', file)
    await flushPromises()

    expect(getExpose(wrapper, 'shareDialogVisible')).toBe(true)
    expect(getExpose(wrapper, 'shareForm')).toMatchObject({
      resource_type: 'file',
      resource_id: 'file-secure-share',
      require_login: false,
      password: '',
      password_hint: '',
      allow_download: true,
      allow_preview: true,
      allow_diff: true,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
    })
  })

  it('submits password and override permissions when creating a file share link', async () => {
    mocks.createShareToken.mockResolvedValueOnce({
      id: 'share-token-1',
      token: 'share-token-1',
      resource_type: 'file',
      resource_id: 'file-secure-share',
      allow_download: false,
      require_login: true,
      password_hint: '项目简称',
      allow_preview: false,
      allow_diff: false,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const openShareDialog = getExpose(wrapper, 'openShareDialog')
    const createShareLink = getExpose(wrapper, 'createShareLink')
    expect(typeof openShareDialog).toBe('function')
    expect(typeof createShareLink).toBe('function')

    await openShareDialog('file', {
      id: 'file-secure-share',
      original_filename: 'restricted.docx',
      filename: 'restricted.docx',
      file_type: 'docx',
      current_version: 1,
    }, {
      policyMode: 'override_with_token_policy',
    })
    await flushPromises()

    const shareForm = getExpose(wrapper, 'shareForm')
    shareForm.require_login = true
    shareForm.password = 'OpenSesame!1'
    shareForm.password_hint = '项目简称'
    shareForm.allow_download = false
    shareForm.allow_preview = false
    shareForm.allow_diff = false
    shareForm.allow_versions = false
    shareForm.policy_mode = 'override_with_token_policy'
    shareForm.expires_at = '2026-07-02T12:00:00'

    await createShareLink()
    await flushPromises()

    expect(mocks.createShareToken).toHaveBeenCalledWith({
      name: expect.any(String),
      resource_type: 'file',
      resource_id: 'file-secure-share',
      require_login: true,
      password: 'OpenSesame!1',
      password_hint: '项目简称',
      allow_download: false,
      allow_preview: false,
      allow_diff: false,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
      max_views: 0,
      max_downloads: 0,
      expires_at: '2026-07-02T12:00:00Z',
    })
  })

  it('reuses the latest existing file share token so secure-share edits stay aligned with current granularity', async () => {
    mocks.listShareTokens.mockResolvedValueOnce({
      items: [
        {
          id: 'share-old',
          token: 'share-old',
          name: '旧分享',
          resource_type: 'file',
          resource_id: 'file-secure-share',
          allow_download: true,
          require_login: false,
          password_hint: '旧口令',
          allow_preview: true,
          allow_diff: true,
          allow_versions: true,
          policy_mode: 'inherit_resource_policy',
          updated_at: '2026-07-01T08:00:00Z',
        },
        {
          id: 'share-current',
          token: 'share-current',
          name: '当前分享',
          resource_type: 'file',
          resource_id: 'file-secure-share',
          allow_download: false,
          require_login: true,
          password_hint: '当前口令',
          allow_preview: false,
          allow_diff: false,
          allow_versions: false,
          policy_mode: 'override_with_token_policy',
          expires_at: '2026-07-03T12:00:00Z',
          updated_at: '2026-07-02T08:00:00Z',
        },
      ],
    })
    mocks.updateShareToken.mockResolvedValueOnce({
      id: 'share-current',
      name: '当前分享',
      resource_type: 'file',
      resource_id: 'file-secure-share',
      allow_download: false,
      require_login: true,
      password_hint: '新提示',
      allow_preview: false,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-04T12:00:00Z',
      updated_at: '2026-07-03T08:00:00Z',
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handleFileRowAction = getExpose(wrapper, 'handleFileRowAction')
    const createShareLink = getExpose(wrapper, 'createShareLink')
    expect(typeof handleFileRowAction).toBe('function')
    expect(typeof createShareLink).toBe('function')

    handleFileRowAction('share-access', {
      id: 'file-secure-share',
      original_filename: 'restricted.docx',
      filename: 'restricted.docx',
      file_type: 'docx',
      current_version: 1,
    })
    await flushPromises()

    expect(mocks.listShareTokens).toHaveBeenCalledTimes(1)
    expect(getExpose(wrapper, 'editingShareToken')).toMatchObject({
      id: 'share-current',
      token: 'share-current',
    })
    expect(getExpose(wrapper, 'shareForm')).toMatchObject({
      name: '当前分享',
      allow_download: false,
      require_login: true,
      password: '',
      clear_password: false,
      password_hint: '当前口令',
      allow_preview: false,
      allow_diff: false,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-03T12:00:00',
    })

    const shareForm = getExpose(wrapper, 'shareForm')
    shareForm.password_hint = '新提示'
    shareForm.allow_versions = true
    shareForm.expires_at = '2026-07-04T12:00:00'

    await createShareLink()
    await flushPromises()

    expect(mocks.createShareToken).not.toHaveBeenCalled()
    expect(mocks.updateShareToken).toHaveBeenCalledWith('share-current', {
      name: '当前分享',
      resource_type: 'file',
      resource_id: 'file-secure-share',
      max_views: 0,
      max_downloads: 0,
      allow_download: false,
      require_login: true,
      password_hint: '新提示',
      allow_preview: false,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-04T12:00:00Z',
    })
  })

  it('can explicitly clear an existing file share password from the secure-share dialog', async () => {
    mocks.listShareTokens.mockResolvedValueOnce({
      items: [
        {
          id: 'share-current',
          token: 'share-current',
          name: '当前分享',
          resource_type: 'file',
          resource_id: 'file-password',
          allow_download: true,
          require_login: true,
          password_hint: '旧口令',
          allow_preview: true,
          allow_diff: true,
          allow_versions: true,
          policy_mode: 'override_with_token_policy',
          updated_at: '2026-07-02T08:00:00Z',
        },
      ],
    })
    mocks.updateShareToken.mockResolvedValueOnce({
      id: 'share-current',
      name: '当前分享',
      resource_type: 'file',
      resource_id: 'file-password',
      allow_download: true,
      require_login: true,
      password_hint: '无口令',
      allow_preview: true,
      allow_diff: true,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    await getExpose(wrapper, 'openShareDialog')('file', {
      id: 'file-password',
      original_filename: 'password.docx',
      filename: 'password.docx',
      file_type: 'docx',
      current_version: 1,
    }, {
      policyMode: 'override_with_token_policy',
    })
    await flushPromises()

    const shareForm = getExpose(wrapper, 'shareForm')
    shareForm.clear_password = true
    shareForm.password_hint = '无口令'

    await getExpose(wrapper, 'createShareLink')()
    await flushPromises()

    expect(mocks.updateShareToken).toHaveBeenCalledWith('share-current', expect.objectContaining({
      password: '',
      password_hint: '无口令',
    }))
  })

  it('reuses the latest existing project share token and resets share state on close', async () => {
    mocks.listShareTokens.mockResolvedValueOnce({
      items: [
        {
          id: 'project-share-old',
          token: 'project-share-old',
          name: '旧项目分享',
          resource_type: 'project',
          resource_id: 'project-1',
          allow_download: true,
          require_login: false,
          password_hint: '旧提示',
          allow_preview: true,
          allow_diff: true,
          allow_versions: true,
          policy_mode: 'inherit_resource_policy',
          updated_at: '2026-07-01T08:00:00Z',
        },
        {
          id: 'project-share-current',
          token: 'project-share-current',
          name: '当前项目分享',
          resource_type: 'project',
          resource_id: 'project-1',
          allow_download: false,
          require_login: true,
          password_hint: '项目口令',
          allow_preview: false,
          allow_diff: false,
          allow_versions: true,
          policy_mode: 'override_with_token_policy',
          expires_at: '2026-07-06T12:00:00Z',
          updated_at: '2026-07-02T08:00:00Z',
        },
      ],
    })
    mocks.updateShareToken.mockResolvedValueOnce({
      id: 'project-share-current',
      name: '当前项目分享',
      resource_type: 'project',
      resource_id: 'project-1',
      allow_download: false,
      require_login: true,
      password_hint: '新项目口令',
      allow_preview: false,
      allow_diff: true,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-07T12:00:00Z',
    })

    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    await getExpose(wrapper, 'openShareDialog')('project')
    await flushPromises()

    expect(getExpose(wrapper, 'editingShareToken')).toMatchObject({
      id: 'project-share-current',
      token: 'project-share-current',
    })
    expect(getExpose(wrapper, 'shareForm')).toMatchObject({
      resource_type: 'project',
      resource_id: 'project-1',
      name: '当前项目分享',
      allow_download: false,
      require_login: true,
      password_hint: '项目口令',
      allow_preview: false,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-06T12:00:00',
    })

    const shareForm = getExpose(wrapper, 'shareForm')
    shareForm.password = 'ProjectPass!2'
    shareForm.password_hint = '新项目口令'
    shareForm.allow_diff = true
    shareForm.expires_at = '2026-07-07T12:00:00'

    await getExpose(wrapper, 'createShareLink')()
    await flushPromises()

    expect(mocks.updateShareToken).toHaveBeenCalledWith('project-share-current', expect.objectContaining({
      resource_type: 'project',
      resource_id: 'project-1',
      password: 'ProjectPass!2',
      password_hint: '新项目口令',
      allow_diff: true,
      expires_at: '2026-07-07T12:00:00Z',
    }))

    getExpose(wrapper, 'closeShareDialog')()

    expect(getExpose(wrapper, 'shareDialogVisible')).toBe(false)
    expect(getExpose(wrapper, 'editingShareToken')).toBe(null)
    expect(getExpose(wrapper, 'shareTarget')).toBe(null)
    expect(getExpose(wrapper, 'shareForm')).toMatchObject({
      resource_type: 'project',
      password: '',
      clear_password: false,
      require_login: false,
    })
  })

  it('renders an inline video player for mp4 previews instead of the iframe fallback', async () => {
    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const handlePreview = getExpose(wrapper, 'handlePreview')
    expect(typeof handlePreview).toBe('function')

    handlePreview({
      id: 'file-video',
      original_filename: 'lesson.mp4',
      filename: 'lesson.mp4',
      file_type: 'mp4',
      current_version: 1,
      updated_at: '2026-06-16T10:00:00Z',
    })
    await flushPromises()

    expect(mocks.buildAuthenticatedPreviewUrl).toHaveBeenLastCalledWith(
      'file-video',
      1,
      'token-123',
      'file-video-v1-open',
    )
    expect(
      mocks.clientGet.mock.calls.some(([url]) => url === '/files/file-video/preview'),
    ).toBe(false)
    expect(wrapper.find('[data-testid="preview-video-player"]').exists()).toBe(true)
    expect(wrapper.find('.preview-iframe-container').exists()).toBe(false)
  })

  it('keeps admin native video previews in a contain box instead of zooming them into a strip', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')
    const blockStart = source.indexOf('.preview-video-player')
    const blockEnd = source.indexOf('.preview-placeholder', blockStart)
    const videoStyleBlock = source.slice(blockStart, blockEnd)

    expect(videoStyleBlock).toContain('.preview-video-player')
    expect(videoStyleBlock).toContain('object-fit: contain;')
    expect(videoStyleBlock).toContain('height: min(70vh, 720px);')
    expect(videoStyleBlock).not.toContain('zoom: var(--admin-preview-scale);')
  })




  it('keeps file list table compact to avoid horizontal scrolling on normal desktop width', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')
    const tableStart = source.indexOf('class="file-table"')
    const tableEnd = source.indexOf('</el-table>', tableStart)
    const tableSource = source.slice(tableStart, tableEnd)

    expect(tableSource).toContain('label="\u4fe1\u606f"')
    expect(tableSource).not.toContain('label="\u5f53\u524d\u7248\u672c"')
    expect(tableSource).not.toContain('label="\u6587\u4ef6\u5927\u5c0f"')
    expect(tableSource).not.toContain('label="\u66f4\u65b0\u65f6\u95f4"')
    expect(tableSource).not.toContain('label="\u64cd\u4f5c" width="520"')
    expect(tableSource).toContain('label="\u64cd\u4f5c" width="232"')
    expect(tableSource).toContain('getPreviewCompactText')
    expect(source).toContain('max-width: 100%;')
  })

  it('uses file display name and selected version inside preview placeholder title', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('<p>{{ getPreviewDialogTitle(previewFile, previewVersion) }}</p>')
    expect(source).not.toContain('<p>????</p>')
  })

  it('uses file display name and selected version as preview dialog title', async () => {
    const wrapper = shallowMount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const getPreviewDialogTitle = getExpose(wrapper, 'getPreviewDialogTitle')
    expect(typeof getPreviewDialogTitle).toBe('function')

    const file = {
      original_filename: 'original.docx',
      filename: 'original.docx',
      display_name: '显示名称.docx',
      current_version: 3,
    }

    expect(getPreviewDialogTitle(file, 2)).toBe('显示名称.docx · v2')
  })

  it('renders mobile file cards instead of the wide table on phones', async () => {
    mocks.responsiveState.isMobile = true
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-mobile',
          filename: 'mobile-preview.pdf',
          original_filename: 'mobile-preview.pdf',
          file_type: 'pdf',
          current_version: 3,
          updated_at: '2026-06-16T10:00:00Z',
          file_size: 1024,
          tags: [],
        },
      ],
    })
    mocks.getPreviewStatuses.mockResolvedValueOnce({
      files: [{ file_id: 'file-mobile', status: 'ready' }],
      summary: {},
    })

    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    expect(wrapper.find('[data-testid="admin-mobile-file-list"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('mobile-preview.pdf')
    expect(wrapper.text()).toContain('预览')
    expect(wrapper.text()).toContain('分享')
    expect(wrapper.find('.file-table-scroll').exists()).toBe(false)

    mocks.responsiveState.isMobile = false
  })

  it('renders a compact mobile resource shell with collapsible helper copy above file cards', async () => {
    mocks.responsiveState.isMobile = true
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-mobile-shell',
          filename: 'mobile-shell.pdf',
          original_filename: 'mobile-shell.pdf',
          file_type: 'pdf',
          current_version: 1,
          updated_at: '2026-06-16T10:00:00Z',
          file_size: 1024,
          folder_id: '',
          tags: [],
        },
      ],
    })
    mocks.getProjectFolders.mockResolvedValueOnce({
      folders: [{ id: 'folder-mobile', name: '合同资料' }],
    })
    mocks.getPreviewStatuses.mockResolvedValueOnce({ files: [], summary: {} })

    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const shell = wrapper.find('[data-testid="admin-mobile-resource-shell"]')
    expect(shell.exists()).toBe(true)
    expect(shell.text()).toContain('2 个资源')
    expect(wrapper.find('[data-testid="admin-mobile-resource-summary"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="admin-mobile-file-list"]').exists()).toBe(true)

    mocks.responsiveState.isMobile = false
  })

  it('keeps the admin mobile resource shell sticky with blurred safe-area spacing', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('.resource-mobile-shell')
    expect(source).toContain('position: sticky;')
    expect(source).toContain('top: calc(8px + env(safe-area-inset-top));')
    expect(source).toContain('backdrop-filter: blur(14px);')
  })

  it('places folders into the same resource area as files on mobile instead of rendering a standalone top grid', async () => {
    mocks.responsiveState.isMobile = true
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-root',
          filename: 'root-file.pdf',
          original_filename: 'root-file.pdf',
          file_type: 'pdf',
          current_version: 1,
          updated_at: '2026-06-16T10:00:00Z',
          file_size: 1024,
          folder_id: '',
          tags: [],
        },
      ],
    })
    mocks.getProjectFolders.mockResolvedValueOnce({
      folders: [
        { id: 'folder-a', name: '合同资料' },
      ],
    })
    mocks.getPreviewStatuses.mockResolvedValueOnce({ files: [], summary: {} })

    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const resourceItems = getExpose(wrapper, 'resourceItems')
    const normalizedResourceItems = Array.isArray(resourceItems)
      ? resourceItems
      : (resourceItems?.value || [])

    expect(normalizedResourceItems.map((item) => item.type)).toEqual(['folder', 'file'])
    expect(wrapper.find('.folder-grid').exists()).toBe(false)
    expect(wrapper.find('[data-testid="resource-folder-item-folder-a"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('合同资料')
    expect(wrapper.text()).toContain('root-file.pdf')

    mocks.responsiveState.isMobile = false
  })

  it('binds the desktop table to mixed resource rows and removes the standalone folder grid', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain(':data="resourceItems"')
    expect(source).toContain('@row-click="handleResourceRowClick"')
    expect(source).toContain('@click.stop="openFolder(row.resourceId)"')
    expect(source).not.toContain('class="resource-folder-list"')
  })

  it('keeps folders before files in resourceItems and opens folder rows with a single row click', async () => {
    mocks.getProject.mockResolvedValueOnce({
      id: 'project-1',
      name: 'Project One',
      description: 'desc',
      files: [
        {
          id: 'file-root',
          filename: 'root-file.pdf',
          original_filename: 'root-file.pdf',
          file_type: 'pdf',
          current_version: 1,
          updated_at: '2026-06-16T10:00:00Z',
          file_size: 1024,
          folder_id: '',
          tags: [],
        },
      ],
    })
    mocks.getProjectFolders.mockResolvedValueOnce({
      folders: [{ id: 'folder-a', name: '合同资料' }],
    })
    mocks.getPreviewStatuses.mockResolvedValueOnce({ files: [], summary: {} })

    const wrapper = mount(ProjectDetail, globalMountOptions)
    await flushPromises()

    const resourceItems = getExpose(wrapper, 'resourceItems')
    const normalizedItems = Array.isArray(resourceItems) ? resourceItems : (resourceItems?.value || [])
    expect(normalizedItems.map((item) => item.type)).toEqual(['folder', 'file'])

    const handleResourceRowClick = getExpose(wrapper, 'handleResourceRowClick')
    expect(typeof handleResourceRowClick).toBe('function')

    handleResourceRowClick(normalizedItems[0])
    await flushPromises()

    expect(mocks.routerReplace).toHaveBeenLastCalledWith({
      path: '/admin/projects/project-1',
      query: { folder_id: 'folder-a' },
      hash: '',
    })
  })

  it('keeps a dedicated preview scale token in the admin preview dialog styles', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('--admin-preview-scale')
    expect(source).toContain('zoom: var(--admin-preview-scale)')
  })

  it('uses a reduced centered admin preview shell instead of the old oversized iframe fill', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('--admin-preview-scale: 0.82;')
    expect(source).toContain('justify-content: center;')
    expect(source).toContain('background: #f5f7fb;')
  })

  it('uses the same compact parent-card copy on admin mobile resource cards as the share side', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')
    const mobileBlockStart = source.indexOf('<FileListCards')
    const mobileBlockEnd = source.indexOf('</FileListCards>', mobileBlockStart)
    const mobileBlock = source.slice(mobileBlockStart, mobileBlockEnd)

    expect(mobileBlock).toContain('<span v-else-if="item.type === \'parent\'">返回上一级</span>')
    expect(mobileBlock).toContain('回到根目录')
    expect(mobileBlock).not.toContain('快速返回上一层')
    expect(mobileBlock).not.toContain('上一级</el-tag>')
  })

  it('wraps admin mobile resource controls instead of forcing horizontal breadcrumb scrolling', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ProjectDetail.vue'), 'utf-8')
    const mobileStart = source.indexOf('@media (max-width: 768px)')
    const mobileBlock = source.slice(mobileStart)

    expect(mobileBlock).toContain('.resource-breadcrumb')
    expect(mobileBlock).toContain('flex-wrap: wrap;')
    expect(mobileBlock).toContain('white-space: normal;')
    expect(mobileBlock).not.toContain('overflow-x: auto;')
  })

  it('uses an auto-fit mobile action grid for resource cards instead of a rigid two-column clamp', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(
      path.resolve(__dirname, '../../../components/file/FileListCards.vue'),
      'utf-8',
    )

    expect(source).toContain('repeat(auto-fit, minmax(132px, 1fr))')
    expect(source).toContain('white-space: normal;')
  })

  it('shows fixed independent share-permission copy in the secure-share dialog instead of a policy-mode selector', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ProjectDetail.vue'), 'utf-8')

    expect(source).toContain('分享权限仅作用于分享链接，不继承公开浏览权限。')
    expect(source).not.toContain('label="策略模式"')
    expect(source).not.toContain('sharePolicyModeOptions')
  })

})
