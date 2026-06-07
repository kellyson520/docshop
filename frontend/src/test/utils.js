/**
 * 测试工具函数
 * 提供常用的测试辅助函数，简化组件测试的编写
 */
import { render } from '@testing-library/vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { vi } from 'vitest'
import ElementPlus from 'element-plus'

// ==================== Pinia Store 相关工具 ====================

/**
 * 创建带 Pinia 的渲染函数
 * 用于测试需要访问 Pinia Store 的组件
 *
 * @param {Object} component - 要渲染的 Vue 组件
 * @param {Object} options - 渲染选项
 * @param {Object} options.initialState - Pinia Store 的初始状态
 * @param {Object} options.pinia - 自定义 Pinia 实例
 * @returns {Object} 渲染结果和 Pinia 实例
 *
 * @example
 * const { getByText, pinia } = renderWithPinia(MyComponent, {
 *   initialState: { user: { name: 'Test User' } }
 * })
 */
export function renderWithPinia(component, options = {}) {
  const { initialState = {}, pinia: customPinia, ...renderOptions } = options

  // 创建 Pinia 实例
  const pinia = customPinia || createPinia()

  // 如果有初始状态，设置到 Pinia 中
  if (Object.keys(initialState).length > 0) {
    // 设置初始状态到 Pinia 的 state
    pinia.state.value = { ...pinia.state.value, ...initialState }
  }

  // 渲染组件
  const result = render(component, {
    global: {
      plugins: [pinia, ElementPlus]
    },
    ...renderOptions
  })

  return {
    ...result,
    pinia
  }
}

/**
 * 创建 Mock Store
 * 用于创建模拟的 Pinia Store，方便控制测试行为
 *
 * @param {Object} storeDefinition - Store 定义对象
 * @param {Object} mockState - 要模拟的状态
 * @param {Object} mockActions - 要模拟的方法
 * @returns {Object} Mock Store 实例
 *
 * @example
 * const mockStore = createMockStore(useUserStore, {
 *   user: { id: 1, name: 'Test' },
 *   isLoggedIn: true
 * }, {
 *   login: vi.fn(),
 *   logout: vi.fn()
 * })
 */
export function createMockStore(storeDefinition, mockState = {}, mockActions = {}) {
  return {
    ...mockState,
    ...mockActions,
    $patch: vi.fn(),
    $reset: vi.fn(),
    $subscribe: vi.fn(),
    $onAction: vi.fn()
  }
}

// ==================== 路由相关工具 ====================

/**
 * 创建带路由的渲染函数
 * 用于测试需要访问 Vue Router 的组件
 *
 * @param {Object} component - 要渲染的 Vue 组件
 * @param {Object} options - 渲染选项
 * @param {Array} options.routes - 路由配置数组
 * @param {string} options.initialRoute - 初始路由路径
 * @param {Object} options.router - 自定义 Router 实例
 * @returns {Object} 渲染结果和 Router 实例
 *
 * @example
 * const { getByText, router } = renderWithRouter(MyComponent, {
 *   routes: [{ path: '/', component: Home }],
 *   initialRoute: '/'
 * })
 */
export function renderWithRouter(component, options = {}) {
  const {
    routes = [{ path: '/', component: { template: '<div>Home</div>' } }],
    initialRoute = '/',
    router: customRouter,
    ...renderOptions
  } = options

  // 创建 Router 实例
  const router = customRouter || createRouter({
    history: createWebHistory(),
    routes
  })

  // 设置初始路由
  if (initialRoute) {
    router.push(initialRoute)
  }

  // 渲染组件
  const result = render(component, {
    global: {
      plugins: [router, ElementPlus]
    },
    ...renderOptions
  })

  return {
    ...result,
    router
  }
}

/**
 * 创建 Mock Router
 * 用于创建模拟的路由实例
 *
 * @param {Object} options - 配置选项
 * @param {string} options.currentRoute - 当前路由路径
 * @returns {Object} Mock Router 实例
 */
export function createMockRouter(options = {}) {
  const { currentRoute = '/' } = options

  return {
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    currentRoute: {
      value: {
        path: currentRoute,
        params: {},
        query: {},
        name: undefined,
        fullPath: currentRoute,
        hash: '',
        matched: []
      }
    },
    beforeEach: vi.fn(),
    afterEach: vi.fn(),
    addRoute: vi.fn(),
    removeRoute: vi.fn(),
    hasRoute: vi.fn(() => true),
    resolve: vi.fn((to) => ({ href: to })),
    options: {
      routes: []
    }
  }
}

// ==================== 异步等待工具 ====================

/**
 * 等待加载完成
 * 用于等待异步操作（如数据加载）完成
 *
 * @param {Function} callback - 断言回调函数
 * @param {Object} options - 配置选项
 * @param {number} options.timeout - 超时时间（毫秒），默认 5000
 * @param {number} options.interval - 检查间隔（毫秒），默认 50
 * @returns {Promise} 等待结果
 *
 * @example
 * await waitForLoading(() => {
 *   expect(screen.getByText('加载完成')).toBeInTheDocument()
 * })
 */
export async function waitForLoading(callback, options = {}) {
  const { timeout = 5000, interval = 50 } = options
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    try {
      await callback()
      return
    } catch (error) {
      await new Promise(resolve => setTimeout(resolve, interval))
    }
  }

  throw new Error(`waitForLoading 超时: ${timeout}ms`)
}

/**
 * 等待指定时间
 * 简单的延迟函数
 *
 * @param {number} ms - 等待时间（毫秒）
 * @returns {Promise} 延迟 Promise
 */
export function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 等待元素出现
 * 用于等待 DOM 元素渲染完成
 *
 * @param {Function} queryFn - 查询函数
 * @param {Object} options - 配置选项
 * @param {number} options.timeout - 超时时间（毫秒），默认 5000
 * @returns {Promise} 元素
 */
export async function waitForElement(queryFn, options = {}) {
  const { timeout = 5000 } = options
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    const element = queryFn()
    if (element) {
      return element
    }
    await wait(50)
  }

  throw new Error(`等待元素超时: ${timeout}ms`)
}

// ==================== 事件模拟工具 ====================

/**
 * 模拟文件上传
 * 用于测试文件上传组件
 *
 * @param {HTMLElement} input - 文件输入元素
 * @param {Array} files - 文件数组
 */
export function simulateFileUpload(input, files) {
  const event = {
    target: {
      files
    }
  }
  input.dispatchEvent(new Event('change', event))
}

/**
 * 创建 Mock 文件
 * 用于测试文件相关功能
 *
 * @param {string} name - 文件名
 * @param {number} size - 文件大小（字节）
 * @param {string} type - MIME 类型
 * @returns {File} Mock File 对象
 */
export function createMockFile(name = 'test.txt', size = 1024, type = 'text/plain') {
  const content = new Array(size).fill('a').join('')
  return new File([content], name, { type })
}

// ==================== 表单相关工具 ====================

/**
 * 填充表单字段
 * 自动填充表单中的所有输入字段
 *
 * @param {Object} screen - Testing Library 的 screen 对象
 * @param {Object} formData - 表单数据对象，key 为字段名，value 为字段值
 *
 * @example
 * fillFormFields(screen, {
 *   username: 'testuser',
 *   email: 'test@example.com',
 *   password: 'password123'
 * })
 */
export function fillFormFields(screen, formData) {
  Object.entries(formData).forEach(([name, value]) => {
    const input = screen.getByLabelText(new RegExp(name, 'i')) ||
                  screen.getByPlaceholderText(new RegExp(name, 'i')) ||
                  screen.getByTestId(name)

    if (input) {
      input.setValue(value)
    }
  })
}

/**
 * 获取表单值
 * 获取表单中所有字段的当前值
 *
 * @param {HTMLElement} form - 表单元素
 * @returns {Object} 表单数据对象
 */
export function getFormValues(form) {
  const formData = new FormData(form)
  const values = {}

  formData.forEach((value, key) => {
    values[key] = value
  })

  return values
}

// ==================== 常用 Mock 数据 ====================

/**
 * 创建 Mock 用户
 *
 * @param {Object} overrides - 覆盖默认值的属性
 * @returns {Object} Mock 用户对象
 */
export function createMockUser(overrides = {}) {
  return {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    role: 'user',
    avatar: null,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides
  }
}

/**
 * 创建 Mock 项目
 *
 * @param {Object} overrides - 覆盖默认值的属性
 * @returns {Object} Mock 项目对象
 */
export function createMockProject(overrides = {}) {
  return {
    id: 1,
    name: '测试项目',
    description: '这是一个测试项目',
    owner_id: 1,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
    ...overrides
  }
}

/**
 * 创建 Mock 文件
 *
 * @param {Object} overrides - 覆盖默认值的属性
 * @returns {Object} Mock 文件对象
 */
export function createMockFileData(overrides = {}) {
  return {
    id: 1,
    name: 'test.pdf',
    original_name: '测试文档.pdf',
    path: '/uploads/test.pdf',
    size: 1024000,
    mime_type: 'application/pdf',
    project_id: 1,
    uploaded_by: 1,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides
  }
}

/**
 * 创建 Mock 卡片
 *
 * @param {Object} overrides - 覆盖默认值的属性
 * @returns {Object} Mock 卡片对象
 */
export function createMockCard(overrides = {}) {
  return {
    id: 1,
    title: '测试卡片',
    content: '这是卡片内容',
    status: 'todo',
    priority: 'medium',
    project_id: 1,
    assigned_to: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
    ...overrides
  }
}

/**
 * 创建 Mock 考试
 *
 * @param {Object} overrides - 覆盖默认值的属性
 * @returns {Object} Mock 考试对象
 */
export function createMockExam(overrides = {}) {
  return {
    id: 1,
    title: '测试考试',
    description: '这是一个测试考试',
    duration: 120,
    total_score: 100,
    passing_score: 60,
    status: 'published',
    created_by: 1,
    created_at: '2024-01-01T00:00:00Z',
    start_time: '2024-06-01T09:00:00Z',
    end_time: '2024-06-01T11:00:00Z',
    ...overrides
  }
}

// ==================== 断言辅助工具 ====================

/**
 * 检查元素是否存在
 *
 * @param {Function} queryFn - 查询函数
 * @returns {boolean} 是否存在
 */
export function elementExists(queryFn) {
  try {
    const element = queryFn()
    return element !== null && element !== undefined
  } catch {
    return false
  }
}

/**
 * 获取元素文本内容
 *
 * @param {HTMLElement} element - DOM 元素
 * @returns {string} 文本内容
 */
export function getElementText(element) {
  return element?.textContent?.trim() || ''
}
