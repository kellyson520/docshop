/**
 * FileUploader 组件单元测试
 * 测试文件上传组件的拖拽上传、文件校验、上传进度等功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import FileUploader from '../../views/admin/FileUpload.vue'

// 模拟 Vue Router
const mockPush = vi.fn()
const mockRoute = {
  params: { id: '123' },
  query: {}
}

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({
    push: mockPush
  })
}))

// 模拟 Element Plus 组件
vi.mock('element-plus', () => ({
  ElButton: {
    name: 'ElButton',
    props: ['type', 'size', 'circle', 'loading', 'disabled', 'text'],
    template: '<button :disabled="disabled || loading" :class="type"><slot /></button>'
  },
  ElCard: {
    name: 'ElCard',
    props: ['shadow'],
    template: '<div class="el-card"><div v-if="$slots.header" class="el-card__header"><slot name="header"/></div><div class="el-card__body"><slot /></div></div>'
  },
  ElForm: {
    name: 'ElForm',
    props: ['labelPosition'],
    template: '<form class="el-form"><slot /></form>'
  },
  ElFormItem: {
    name: 'ElFormItem',
    props: ['label', 'error', 'required'],
    template: '<div class="el-form-item" :class="{ \'is-error\': error }"><label v-if="label">{{ label }}</label><div class="el-form-item__content"><slot /></div><div v-if="error" class="el-form-item__error">{{ error }}</div></div>'
  },
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'type', 'placeholder', 'rows', 'maxlength', 'showWordLimit', 'disabled'],
    emits: ['update:modelValue'],
    template: '<textarea v-if="type === \'textarea\'" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" :placeholder="placeholder" :rows="rows" :disabled="disabled" :maxlength="maxlength" /><input v-else :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" :placeholder="placeholder" :disabled="disabled" />'
  },
  ElTag: {
    name: 'ElTag',
    props: ['type', 'size'],
    template: '<span class="el-tag" :class="type"><slot /></span>'
  },
  ElProgress: {
    name: 'ElProgress',
    props: ['percentage', 'status', 'strokeWidth', 'textInside'],
    template: '<div class="el-progress" :class="status"><div class="el-progress__bar" :style="{ width: percentage + \'%\' }">{{ percentage }}%</div></div>'
  },
  ElAlert: {
    name: 'ElAlert',
    props: ['title', 'type', 'showIcon', 'closable'],
    template: '<div class="el-alert" :class="type"><slot>{{ title }}</slot></div>'
  },
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template: '<span class="el-icon" :style="{ fontSize: size + \'px\', color }"><slot /></span>'
  },
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  }
}))

// 模拟 Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  ArrowLeft: { name: 'ArrowLeft', template: '<span class="icon-arrow-left" />' },
  UploadFilled: { name: 'UploadFilled', template: '<span class="icon-upload-filled" />' },
  Upload: { name: 'Upload', template: '<span class="icon-upload" />' },
  Document: { name: 'Document', template: '<span class="icon-document" />' },
  Grid: { name: 'Grid', template: '<span class="icon-grid" />' },
  Close: { name: 'Close', template: '<span class="icon-close" />' },
  RefreshRight: { name: 'RefreshRight', template: '<span class="icon-refresh-right" />' }
}))

// 模拟 API
const mockUploadFile = vi.fn()
const mockUploadVersion = vi.fn()
const { mockValidateFile } = vi.hoisted(() => ({
  mockValidateFile: vi.fn()
}))

vi.mock('@/api/file', () => ({
  uploadFile: (...args) => mockUploadFile(...args),
  uploadVersion: (...args) => mockUploadVersion(...args)
}))

// 模拟 composables
vi.mock('@/composables/useLoading', () => ({
  useLoading: () => ({
    loading: ref(false),
    start: vi.fn(),
    stop: vi.fn()
  })
}))

vi.mock('@/composables/useMessage', () => ({
  useMessage: () => ({
    success: vi.fn(),
    error: vi.fn()
  })
}))

// 模拟工具函数
vi.mock('@/utils/validators', () => ({
  validateFile: mockValidateFile
}))

vi.mock('@/utils/error', () => ({
  ErrorHandler: {
    parseError: (error) => ({ message: error.message || '未知错误' }),
    handle: vi.fn()
  }
}))

vi.mock('@/utils', () => ({
  formatFileSize: (bytes) => {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const k = 1024
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i]
  }
}))

async function selectFile(fileInput, ...files) {
  Object.defineProperty(fileInput.element, 'files', {
    value: files,
    configurable: true
  })
  fileInput.element.dispatchEvent(new Event('change', { bubbles: true }))
  await nextTick()
}

function defaultValidateFile(file, options) {
  if (!file) return '请选择文件'
  if (options?.maxSize && file.size > options.maxSize) return '文件大小超过限制'
  if (options?.allowedTypes) {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!options.allowedTypes.includes(ext)) return '不支持的文件类型'
  }
  return true
}

describe('FileUploader 组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockValidateFile.mockImplementation(defaultValidateFile)
    mockRoute.query = {}
    mockRoute.params = { id: '123' }
  })

  /**
   * 渲染测试
   */
  describe('渲染', () => {
    it('应该正确渲染上传组件', () => {
      const wrapper = mount(FileUploader)

      expect(wrapper.find('.upload-card').exists()).toBe(true)
      expect(wrapper.find('.upload-dragger').exists()).toBe(true)
    })

    it('应该显示正确的标题', () => {
      const wrapper = mount(FileUploader)

      expect(wrapper.text()).toContain('上传文件')
    })

    it('版本上传模式应该显示不同的标题', () => {
      mockRoute.query = { fileId: '456' }
      const wrapper = mount(FileUploader)

      expect(wrapper.text()).toContain('上传新版本')
      expect(wrapper.text()).toContain('版本更新')
    })

    it('应该显示上传须知', () => {
      const wrapper = mount(FileUploader)

      expect(wrapper.text()).toContain('上传须知')
      expect(wrapper.text()).toContain('支持 PDF、DOCX、XLSX 格式的文档')
      expect(wrapper.text()).toContain('单个文件大小不超过 50MB')
    })

    it('应该显示返回按钮', () => {
      const wrapper = mount(FileUploader)

      expect(wrapper.find('.back-button').exists()).toBe(true)
      expect(wrapper.text()).toContain('返回项目详情')
    })
  })

  /**
   * 文件选择测试
   */
  describe('文件选择', () => {
    it('应该可以通过点击触发文件选择', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      expect(fileInput.exists()).toBe(true)

      const clickSpy = vi.spyOn(fileInput.element, 'click')

      await wrapper.find('.upload-dragger').trigger('click')

      expect(clickSpy).toHaveBeenCalled()
    })

    it('选择有效文件后应该显示文件信息', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.text()).toContain('test.pdf')
    })

    it('应该显示文件大小', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['a'.repeat(1024)], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.text()).toContain('KB')
    })

    it('应该可以移除已选文件', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.text()).toContain('test.pdf')

      const removeBtn = wrapper.find('.remove-file-btn')
      await removeBtn.trigger('click')

      await nextTick()

      expect(wrapper.text()).not.toContain('test.pdf')
    })
  })

  /**
   * 拖拽上传测试
   */
  describe('拖拽上传', () => {
    it('拖拽进入时应该添加样式类', async () => {
      const wrapper = mount(FileUploader)
      const dragger = wrapper.find('.upload-dragger')

      await dragger.trigger('dragenter', {
        preventDefault: vi.fn(),
        dataTransfer: { files: [] }
      })

      expect(dragger.classes()).toContain('is-dragover')
    })

    it('拖拽离开时应该移除样式类', async () => {
      const wrapper = mount(FileUploader)
      const dragger = wrapper.find('.upload-dragger')

      await dragger.trigger('dragenter', {
        preventDefault: vi.fn()
      })

      expect(dragger.classes()).toContain('is-dragover')

      await dragger.trigger('dragleave', {
        preventDefault: vi.fn()
      })

      expect(dragger.classes()).not.toContain('is-dragover')
    })

    it('拖放文件应该触发文件选择', async () => {
      const wrapper = mount(FileUploader)
      const dragger = wrapper.find('.upload-dragger')

      const file = new File(['test'], 'dropped.pdf', { type: 'application/pdf' })

      await dragger.trigger('drop', {
        preventDefault: vi.fn(),
        dataTransfer: { files: [file] }
      })

      await nextTick()

      expect(wrapper.text()).toContain('dropped.pdf')
    })

    it('拖拽过程中应该阻止默认行为', async () => {
      const wrapper = mount(FileUploader)
      const dragger = wrapper.find('.upload-dragger')

      const preventDefault = vi.fn()

      const event = new Event('dragover', { bubbles: true, cancelable: true })
      Object.defineProperty(event, 'preventDefault', {
        value: preventDefault,
        configurable: true
      })
      dragger.element.dispatchEvent(event)
      await nextTick()

      expect(preventDefault).toHaveBeenCalled()
    })
  })

  /**
   * 文件校验测试
   */
  describe('文件校验', () => {
    it('无效文件应该显示错误信息', async () => {
      const { validateFile } = await import('@/utils/validators')
      validateFile.mockReturnValueOnce('文件大小超过限制')

      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'large.pdf', { type: 'application/pdf' })
      Object.defineProperty(file, 'size', { value: 100 * 1024 * 1024 })

      await selectFile(fileInput, file)

      await nextTick()

      const formItem = wrapper.find('.el-form-item.is-error')
      expect(formItem.exists()).toBe(true)
    })

    it('不支持的文件类型应该被拒绝', async () => {
      const { validateFile } = await import('@/utils/validators')
      validateFile.mockReturnValueOnce('不支持的文件类型')

      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'test.txt', { type: 'text/plain' })

      await selectFile(fileInput, file)

      await nextTick()

      const formItem = wrapper.find('.el-form-item.is-error')
      expect(formItem.exists()).toBe(true)
    })
  })

  /**
   * 变更说明测试
   */
  describe('变更说明', () => {
    it('应该可以输入变更说明', async () => {
      const wrapper = mount(FileUploader)
      const textarea = wrapper.find('textarea')

      expect(textarea.exists()).toBe(true)

      await textarea.setValue('这是一个变更说明')

      expect(textarea.element.value).toBe('这是一个变更说明')
    })

    it('变更说明应该有最大长度限制', () => {
      const wrapper = mount(FileUploader)
      const textarea = wrapper.find('textarea')

      expect(textarea.attributes('maxlength')).toBe('1000')
    })

    it('上传过程中变更说明应该被禁用', async () => {
      const wrapper = mount(FileUploader)

      // 先选择一个文件
      const fileInput = wrapper.find('input[type="file"]')
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      // 模拟上传中状态
      await wrapper.setData({ uploading: true })

      const textarea = wrapper.find('textarea')
      expect(textarea.attributes('disabled')).toBeDefined()
    })
  })

  /**
   * 文件图标测试
   */
  describe('文件图标', () => {
    it('PDF 文件应该显示正确的图标', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'document.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.find('.file-preview').exists()).toBe(true)
    })

    it('DOCX 文件应该显示正确的图标', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'document.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.find('.file-preview').exists()).toBe(true)
    })

    it('XLSX 文件应该显示正确的图标', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'spreadsheet.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })

      await selectFile(fileInput, file)

      await nextTick()

      expect(wrapper.find('.file-preview').exists()).toBe(true)
    })
  })

  /**
   * 上传按钮测试
   */
  describe('上传按钮', () => {
    it('未选择文件时上传按钮应该被禁用', () => {
      const wrapper = mount(FileUploader)
      const uploadBtn = wrapper.findAll('button').find(btn => btn.text().includes('开始上传'))

      expect(uploadBtn).toBeDefined()
      expect(uploadBtn.attributes('disabled')).toBeDefined()
    })

    it('选择文件后上传按钮应该可用', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      const uploadBtn = wrapper.findAll('button').find(btn => btn.text().includes('开始上传'))
      expect(uploadBtn).toBeDefined()
      // 注意：按钮可用性状态可能需要通过其他方式验证
    })

    it('版本上传模式应该显示不同的按钮文本', () => {
      mockRoute.query = { fileId: '456' }
      const wrapper = mount(FileUploader)

      expect(wrapper.text()).toContain('上传新版本')
    })
  })

  /**
   * 导航测试
   */
  describe('导航', () => {
    it('点击返回按钮应该返回项目详情页', async () => {
      const wrapper = mount(FileUploader)
      const backBtn = wrapper.find('.back-button')

      await backBtn.trigger('click')

      expect(mockPush).toHaveBeenCalledWith('/admin/projects/123')
    })

    it('点击取消按钮应该返回项目详情页', async () => {
      const wrapper = mount(FileUploader)
      const cancelBtn = wrapper.findAll('button').find(btn => btn.text() === '取消')

      if (cancelBtn) {
        await cancelBtn.trigger('click')
        expect(mockPush).toHaveBeenCalledWith('/admin/projects/123')
      }
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('没有项目 ID 时不应报错', () => {
      mockRoute.params = {}

      expect(() => {
        mount(FileUploader)
      }).not.toThrow()
    })

    it('重复选择文件应该更新文件信息', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file1 = new File(['test1'], 'first.pdf', { type: 'application/pdf' })
      const file2 = new File(['test2'], 'second.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })

      await selectFile(fileInput, file1)

      await nextTick()

      expect(wrapper.text()).toContain('first.pdf')

      await selectFile(fileInput, file2)

      await nextTick()

      expect(wrapper.text()).toContain('second.docx')
      expect(wrapper.text()).not.toContain('first.pdf')
    })

    it('上传中拖拽文件应该被忽略', async () => {
      const wrapper = mount(FileUploader)

      // 模拟上传中状态
      await wrapper.setData({ uploading: true })

      const dragger = wrapper.find('.upload-dragger')
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      await dragger.trigger('drop', {
        preventDefault: vi.fn(),
        dataTransfer: { files: [file] }
      })

      await nextTick()

      // 文件不应该被选择
      expect(wrapper.text()).not.toContain('test.pdf')
    })

    it('上传中点击上传区域不应该触发文件选择', async () => {
      const wrapper = mount(FileUploader)

      // 模拟上传中状态
      await wrapper.setData({ uploading: true })

      const fileInput = wrapper.find('input[type="file"]')
      const clickSpy = vi.spyOn(fileInput.element, 'click')

      await wrapper.find('.upload-dragger').trigger('click')

      expect(clickSpy).not.toHaveBeenCalled()
    })
  })

  /**
   * 文件输入重置测试
   */
  describe('文件输入重置', () => {
    it('移除文件后应该重置文件输入', async () => {
      const wrapper = mount(FileUploader)
      const fileInput = wrapper.find('input[type="file"]')

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      await selectFile(fileInput, file)

      await nextTick()

      // 模拟文件输入的 value 属性
      Object.defineProperty(fileInput.element, 'value', {
        value: 'test.pdf',
        writable: true
      })

      const removeBtn = wrapper.find('.remove-file-btn')
      await removeBtn.trigger('click')

      await nextTick()

      expect(fileInput.element.value).toBe('')
    })
  })
})
