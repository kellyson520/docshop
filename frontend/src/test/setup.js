/**
 * 测试前置配置文件
 * 在每个测试文件运行前执行，用于配置全局测试环境
 */
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/vue'
import * as matchers from '@testing-library/jest-dom/matchers'
import { h } from 'vue'
import { config } from '@vue/test-utils'

// 导入 MSW 服务器
import { server } from './mocks/server.js'

// 扩展 Vitest 的 expect 方法，添加 jest-dom 的 DOM 断言
expect.extend(matchers)

// ==================== MSW 服务器配置 ====================

// 在所有测试开始前启动 MSW 服务器
beforeAll(() => {
  // 启动服务器并监听请求
  server.listen({ onUnhandledRequest: 'error' })
})

// 每个测试结束后重置 MSW 处理器
afterEach(() => {
  // 重置处理器到初始状态
  server.resetHandlers()
  // 清理 Vue 测试库创建的 DOM
  cleanup()
})

// 所有测试结束后关闭 MSW 服务器
afterAll(() => {
  server.close()
})

// ==================== 全局 Mock 配置 ====================

// Mock window.matchMedia（Element Plus 等组件库依赖）
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // 已弃用
    removeListener: vi.fn(), // 已弃用
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// Mock IntersectionObserver（虚拟滚动等组件依赖）
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback
  }
  observe() { return null }
  unobserve() { return null }
  disconnect() { return null }
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver
})

// Mock ResizeObserver（响应式布局依赖）
class MockResizeObserver {
  constructor(callback) {
    this.callback = callback
  }
  observe() { return null }
  unobserve() { return null }
  disconnect() { return null }
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: MockResizeObserver
})

// Mock scrollTo（平滑滚动依赖）
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn()
})

// Mock localStorage
// 注意：vitest.config.js 开启了 mockReset，vi.fn 的实现会在每个用例前被重置。
// 这里必须使用普通函数，否则 getItem/setItem 会退化为返回 undefined，导致依赖
// localStorage 初始状态的 store 测试不稳定。
const localStorageData = new Map()
const localStorageMock = {
  getItem(key) {
    return localStorageData.has(key) ? localStorageData.get(key) : null
  },
  setItem(key, value) {
    localStorageData.set(key, String(value))
  },
  removeItem(key) {
    localStorageData.delete(key)
  },
  clear() {
    localStorageData.clear()
  },
  key(index) {
    return Array.from(localStorageData.keys())[index] || null
  },
  get length() {
    return localStorageData.size
  }
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
  configurable: true
})

// ==================== Element Plus Mock ====================

// Mock Element Plus 的 ElMessage 组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    },
    ElMessageBox: {
      confirm: vi.fn(() => Promise.resolve()),
      alert: vi.fn(() => Promise.resolve()),
      prompt: vi.fn(() => Promise.resolve({ value: '' }))
    },
    ElNotification: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    }
  }
})

// Mock Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Plus: { name: 'Plus', render: () => null },
  Minus: { name: 'Minus', render: () => null },
  Edit: { name: 'Edit', render: () => null },
  Delete: { name: 'Delete', render: () => null },
  Search: { name: 'Search', render: () => null },
  Refresh: { name: 'Refresh', render: () => null },
  View: { name: 'View', render: () => null },
  Download: { name: 'Download', render: () => null },
  Upload: { name: 'Upload', render: () => null },
  Folder: { name: 'Folder', render: () => null },
  FolderOpened: { name: 'FolderOpened', render: () => null },
  Document: { name: 'Document', render: () => null },
  ArrowLeft: { name: 'ArrowLeft', render: () => null },
  ArrowRight: { name: 'ArrowRight', render: () => null },
  ArrowUp: { name: 'ArrowUp', render: () => null },
  ArrowDown: { name: 'ArrowDown', render: () => null },
  Sort: { name: 'Sort', render: () => null },
  Check: { name: 'Check', render: () => null },
  Close: { name: 'Close', render: () => null },
  More: { name: 'More', render: () => null },
  Setting: { name: 'Setting', render: () => null },
  User: { name: 'User', render: () => null },
  Lock: { name: 'Lock', render: () => null },
  HomeFilled: { name: 'HomeFilled', render: () => null },
  Menu: { name: 'Menu', render: () => null },
  WarningFilled: { name: 'WarningFilled', render: () => null },
  DataLine: { name: 'DataLine', render: () => null },
  Box: { name: 'Box', render: () => null },
  Picture: { name: 'Picture', render: () => null },
  Files: { name: 'Files', render: () => null },
  Connection: { name: 'Connection', render: () => null },
  Calendar: { name: 'Calendar', render: () => null }
}))

// Vue Test Utils 全局 Element Plus 轻量组件桩
const passthrough = (name, tag = 'div', extra = {}) => ({
  name,
  props: extra.props || [],
  emits: extra.emits || ['click', 'update:modelValue'],
  setup(props, { slots, emit }) {
    return () => h(tag, {
      class: [extra.className || name.replace(/^El/, 'el-').toLowerCase(), props.type, props.size, props.effect],
      disabled: props.disabled || props.loading || undefined,
      style: extra.style ? extra.style(props) : undefined,
      onClick: (event) => emit('click', event),
      onInput: (event) => emit('update:modelValue', event.target.value)
    }, slots.default?.() || props.title || props.description || '')
  }
})

config.global.components = {
  ...(config.global.components || {}),
  ElIcon: passthrough('ElIcon', 'span', {
    props: ['size', 'color'],
    className: 'el-icon',
    style: (props) => ({ fontSize: props.size ? `${props.size}px` : undefined, color: props.color })
  }),
  ElButton: passthrough('ElButton', 'button', {
    props: ['type', 'size', 'disabled', 'loading', 'text', 'circle'],
    emits: ['click'],
    className: 'el-button'
  }),
  ElButtonGroup: passthrough('ElButtonGroup', 'div', {
    className: 'el-button-group'
  }),
  ElTag: passthrough('ElTag', 'span', {
    props: ['type', 'size', 'effect'],
    className: 'el-tag'
  }),
  ElCard: {
    name: 'ElCard',
    setup(_, { slots }) {
      return () => h('div', { class: 'el-card' }, [
        slots.header ? h('div', { class: 'el-card__header' }, slots.header()) : null,
        h('div', { class: 'el-card__body' }, slots.default?.())
      ])
    }
  },
  ElForm: passthrough('ElForm', 'form', { props: ['model', 'rules', 'labelPosition'], className: 'el-form' }),
  ElFormItem: {
    name: 'ElFormItem',
    props: ['label', 'error', 'required'],
    setup(props, { slots }) {
      return () => h('div', { class: ['el-form-item', props.error ? 'is-error' : ''] }, [
        props.label ? h('label', { class: 'el-form-item__label' }, props.label) : null,
        h('div', { class: 'el-form-item__content' }, slots.default?.()),
        props.error ? h('div', { class: 'el-form-item__error' }, props.error) : null
      ])
    }
  },
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'type', 'placeholder', 'rows', 'maxlength', 'disabled'],
    emits: ['update:modelValue'],
    setup(props, { emit }) {
      return () => h(props.type === 'textarea' ? 'textarea' : 'input', {
        class: 'el-input',
        value: props.modelValue,
        placeholder: props.placeholder,
        rows: props.rows,
        maxlength: props.maxlength,
        disabled: props.disabled || undefined,
        onInput: (event) => emit('update:modelValue', event.target.value)
      })
    }
  },
  ElProgress: passthrough('ElProgress', 'div', { props: ['percentage', 'status'], className: 'el-progress' }),
  ElAlert: passthrough('ElAlert', 'div', { props: ['title', 'type', 'closable'], className: 'el-alert' }),
  ElEmpty: {
    name: 'ElEmpty',
    props: ['description'],
    setup(props, { slots }) {
      return () => h('div', { class: 'el-empty' }, [
        slots.image?.(),
        h('span', props.description || '')
      ])
    }
  },
  ElResult: {
    name: 'ElResult',
    props: ['icon', 'title', 'subTitle'],
    setup(props, { slots }) {
      return () => h('div', { class: 'el-result' }, [
        h('div', { class: 'el-result__title' }, props.title || ''),
        h('div', { class: 'el-result__subtitle' }, props.subTitle || ''),
        slots.extra ? h('div', { class: 'el-result__extra' }, slots.extra()) : null,
        slots.default?.()
      ])
    }
  }
}

// ==================== 其他全局 Mock ====================

// Mock console.error 和 console.warn，过滤掉 Vue 的已知警告
const originalConsoleError = console.error
const originalConsoleWarn = console.warn

console.error = (...args) => {
  // 过滤掉 Vue 的已知警告信息
  if (
    args[0]?.includes?.('Vue warn') ||
    args[0]?.includes?.('Failed to resolve component')
  ) {
    return
  }
  originalConsoleError.apply(console, args)
}

console.warn = (...args) => {
  // 过滤掉已知的警告信息
  if (
    args[0]?.includes?.('feature is experimental') ||
    args[0]?.includes?.('deprecated')
  ) {
    return
  }
  originalConsoleWarn.apply(console, args)
}
