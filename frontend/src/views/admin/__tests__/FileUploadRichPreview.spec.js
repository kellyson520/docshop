import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FileUpload from '../FileUpload.vue'

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  clientGet: vi.fn(),
  validateFile: vi.fn(() => true),
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
  uploadFile: vi.fn(),
  uploadVersion: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  default: {
    get: mocks.clientGet,
  },
}))

vi.mock('@/composables/useLoading', () => ({
  useLoading: () => ({
    loading: { value: false },
    start: vi.fn(),
    stop: vi.fn(),
  }),
}))

vi.mock('@/composables/useMessage', () => ({
  useMessage: () => ({
    success: mocks.messageSuccess,
    error: mocks.messageError,
  }),
}))

vi.mock('@/utils/validators', () => ({
  validateFile: mocks.validateFile,
}))

vi.mock('@/utils/error', () => ({
  ErrorHandler: {
    parseError: (error) => ({ message: error?.message || '上传失败' }),
    handle: vi.fn(),
  },
}))

vi.mock('@/utils', () => ({
  formatFileSize: (size) => `${size} B`,
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

describe('FileUpload rich preview hints', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.clientGet.mockResolvedValue({
      file_types: ['.pdf', '.docx', '.html', '.mp4'],
    })
  })

  it('shows archive preview capabilities after selecting a 7z file', async () => {
    const wrapper = mount(FileUpload, globalMountOptions)
    const file = new File(['archive'], 'bundle.7z', { type: 'application/x-7z-compressed' })

    const handleFileSelect = getExpose(wrapper, 'handleFileSelect')

    handleFileSelect({ target: { files: [file] } })
    await flushPromises()

    expect(wrapper.text()).toContain('支持结构预览')
    expect(wrapper.text()).toContain('支持结构对比')
  })

  it('uses security settings file_types for html uploads', async () => {
    const wrapper = mount(FileUpload, globalMountOptions)
    await flushPromises()

    const file = new File(['<html></html>'], 'index.html', { type: 'text/html' })
    const handleFileSelect = getExpose(wrapper, 'handleFileSelect')

    handleFileSelect({ target: { files: [file] } })
    await flushPromises()

    expect(mocks.clientGet).toHaveBeenCalledWith('/settings')
    expect(mocks.validateFile).toHaveBeenCalledWith(
      file,
      expect.objectContaining({
        allowedTypes: expect.arrayContaining(['.html', '.mp4']),
      }),
    )
    expect(wrapper.find('input[type="file"]').attributes('accept')).toContain('.html')
  })
})
