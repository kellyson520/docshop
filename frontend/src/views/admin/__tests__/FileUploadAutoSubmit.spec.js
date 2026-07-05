import { describe, expect, it, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import FileUpload from '../FileUpload.vue'

const mocks = vi.hoisted(() => ({
  uploadFile: vi.fn(),
  uploadVersion: vi.fn(),
  routerPush: vi.fn(),
  route: {
    params: { id: 'project-1' },
    query: {},
  },
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.routerPush }),
}))

vi.mock('@/api/file', () => ({
  uploadFile: mocks.uploadFile,
  uploadVersion: mocks.uploadVersion,
}))

vi.mock('@/composables/useLoading', () => ({
  useLoading: () => ({
    loading: { value: false },
    start: vi.fn(() => {}),
    stop: vi.fn(() => {}),
  }),
}))

vi.mock('@/composables/useMessage', () => ({
  useMessage: () => ({
    success: mocks.messageSuccess,
    error: mocks.messageError,
  }),
}))

vi.mock('@/utils/validators', () => ({
  validateFile: () => true,
}))

vi.mock('@/utils/error', () => ({
  ErrorHandler: {
    parseError: (error) => ({ message: error?.message || '上传失败' }),
    handle: vi.fn(),
  },
}))

vi.mock('@/utils', () => ({
  formatFileSize: () => '1 KB',
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: mocks.messageSuccess,
    error: mocks.messageError,
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  ArrowLeft: { template: '<i />' },
  UploadFilled: { template: '<i />' },
  Upload: { template: '<i />' },
  Document: { template: '<i />' },
  Grid: { template: '<i />' },
  Close: { template: '<i />' },
  RefreshRight: { template: '<i />' },
}))

const globalMountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
      ElCard: { template: '<div><slot name="header" /><slot /></div>' },
      ElForm: { template: '<form><slot /></form>' },
      ElFormItem: { template: '<div><slot /></div>' },
      ElIcon: { template: '<i><slot /></i>' },
      ElTag: { template: '<span><slot /></span>' },
      ElInput: { template: '<textarea />' },
      ElProgress: { template: '<div />' },
      ElAlert: { template: '<div />' },
    },
  },
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('FileUpload select then manual submit', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.route.params = { id: 'project-1' }
    mocks.route.query = {}
    mocks.uploadFile.mockImplementation((_projectId, _file, _changelog, onProgress) => {
      onProgress?.(100)
      return Promise.resolve({ id: 'file-1' })
    })
    vi.useFakeTimers()
  })

  it('selects a valid file without uploading so changelog can be entered before manual submit', async () => {
    const wrapper = shallowMount(FileUpload, globalMountOptions)
    const handleFileSelect = getExpose(wrapper, 'handleFileSelect')
    const handleUpload = getExpose(wrapper, 'handleUpload')
    const file = new File(['hello'], 'manual.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    handleFileSelect({ target: { files: [file] } })
    await flushPromises()

    expect(mocks.uploadFile).not.toHaveBeenCalled()

    wrapper.vm.changelog = '补充变更说明'
    await handleUpload()

    expect(mocks.uploadFile).toHaveBeenCalledTimes(1)
    expect(mocks.uploadFile).toHaveBeenCalledWith('project-1', file, '补充变更说明', expect.any(Function), { folder_id: '' })
  })


  it('uses concise upload copy after selecting a file', async () => {
    const wrapper = shallowMount(FileUpload, globalMountOptions)
    const handleFileSelect = getExpose(wrapper, 'handleFileSelect')
    const uploadButtonText = getExpose(wrapper, 'uploadButtonText')
    const file = new File(['hello'], 'copy.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    expect(uploadButtonText).toBe('\u5f00\u59cb\u4e0a\u4f20')

    handleFileSelect({ target: { files: [file] } })
    await flushPromises()

    expect(mocks.messageSuccess).toHaveBeenCalledWith('\u6587\u4ef6\u5df2\u9009\u62e9')
    expect(uploadButtonText).toBe('\u5f00\u59cb\u4e0a\u4f20')
    expect(mocks.uploadFile).not.toHaveBeenCalled()
  })

  it('does not reopen the file chooser from bubbled input clicks', async () => {
    const wrapper = shallowMount(FileUpload, globalMountOptions)
    const triggerFileInput = getExpose(wrapper, 'triggerFileInput')
    const input = wrapper.find('input[type="file"]').element
    const click = vi.spyOn(input, 'click').mockImplementation(() => {})

    triggerFileInput({ target: input })

    expect(click).not.toHaveBeenCalled()
  })

})
