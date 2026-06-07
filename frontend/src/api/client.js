/**
 * API 客户端
 * 基于 Axios 封装的 HTTP 客户端，提供请求重试、取消（AbortController）、缓存、拦截器等功能
 */

import axios from 'axios'
import { ErrorHandler } from '@/utils/error'
import router from '@/router'

/**
 * 请求配置选项
 */
const DEFAULT_CONFIG = {
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  // 重试配置
  retry: {
    count: 3,           // 最大重试次数
    delay: 1000,        // 重试延迟（毫秒）
    retryCondition: (error) => {
      // 只在网络错误或 5xx 服务器错误时重试
      return !error.response || error.response.status >= 500
    }
  }
}

/**
 * 创建 Axios 实例
 */
const client = axios.create(DEFAULT_CONFIG)

/**
 * 存储正在进行的请求（用于取消）
 * Map<requestKey, AbortController>
 */
const pendingRequests = new Map()

/**
 * 生成请求唯一标识
 * @param {Object} config - 请求配置
 * @returns {string} 请求标识
 */
function stableStringify(value) {
  if (!value) return '{}'
  if (typeof FormData !== 'undefined' && value instanceof FormData) return '[FormData]'
  if (typeof URLSearchParams !== 'undefined' && value instanceof URLSearchParams) return value.toString()
  if (typeof value !== 'object') return String(value)
  const normalized = {}
  Object.keys(value)
    .filter((key) => key !== '_t')
    .sort()
    .forEach((key) => {
      const item = value[key]
      if (item !== undefined) normalized[key] = item
    })
  return JSON.stringify(normalized)
}

function generateRequestKey(config) {
  const paramsKey = stableStringify(config.params)
  const dataKey = ['post', 'put', 'patch', 'delete'].includes(config.method)
    ? stableStringify(config.data)
    : '{}'
  return `${config.method}&${config.url}&${paramsKey}&${dataKey}`
}

/**
 * 添加请求到 pending 列表（使用 AbortController）
 * @param {Object} config - 请求配置
 */
function addPendingRequest(config) {
  const key = generateRequestKey(config)
  // 如果存在相同请求，先取消之前的
  if (pendingRequests.has(key)) {
    pendingRequests.get(key).abort('重复请求被取消')
  }
  const controller = new AbortController()
  config.signal = controller.signal
  pendingRequests.set(key, controller)
}

/**
 * 从 pending 列表移除请求
 * @param {Object} config - 请求配置
 */
function removePendingRequest(config) {
  const key = generateRequestKey(config)
  pendingRequests.delete(key)
}

/**
 * 取消所有正在进行的请求
 */
export function cancelAllRequests() {
  pendingRequests.forEach((controller) => {
    controller.abort('用户主动取消')
  })
  pendingRequests.clear()
}

// ==================== 请求缓存层 ====================

/**
 * 简易内存缓存（LRU 淘汰，上限 200 条）
 * 支持对 GET 请求进行缓存，可配置缓存过期时间
 */
const MAX_CACHE_SIZE = 200
const requestCache = new Map()

/**
 * 缓存配置
 * @typedef {Object} CacheConfig
 * @property {number} [ttl=60000] - 缓存过期时间（毫秒），默认 60 秒
 */

/**
 * 从缓存中获取数据
 * @param {string} key - 缓存键
 * @returns {any|null} 缓存数据，不存在或已过期返回 null
 */
function getCache(key) {
  if (!requestCache.has(key)) return null
  const entry = requestCache.get(key)
  // 检查是否过期
  if (Date.now() - entry.timestamp > entry.ttl) {
    requestCache.delete(key)
    return null
  }
  return entry.data
}

/**
 * 设置缓存数据
 * @param {string} key - 缓存键
 * @param {any} data - 缓存数据
 * @param {number} [ttl=60000] - 过期时间（毫秒）
 */
function setCache(key, data, ttl = 60000) {
  // LRU 淘汰：超出上限时删除最旧的条目
  if (requestCache.size >= MAX_CACHE_SIZE) {
    const oldest = requestCache.keys().next().value
    if (oldest) requestCache.delete(oldest)
  }
  requestCache.set(key, { data, timestamp: Date.now(), ttl })
}

/**
 * 清除所有缓存
 */
export function clearCache() {
  requestCache.clear()
}

/**
 * 清除指定 URL 模式的缓存
 * @param {string} [pattern] - URL 匹配模式（可选），不传则清除全部
 */
export function clearCacheByPattern(pattern) {
  if (!pattern) {
    requestCache.clear()
    return
  }
  for (const key of requestCache.keys()) {
    if (key.includes(pattern)) {
      requestCache.delete(key)
    }
  }
}

// ==================== Blob 错误处理 ====================

/**
 * 检查 blob 响应是否实际为 JSON 错误
 * 当后端返回错误时，responseType: 'blob' 可能收到 JSON 格式的错误信息
 * @param {Blob} blob - 响应 Blob
 * @returns {Promise<Blob>} 原始 Blob 或解析后的错误
 */
async function parseBlobResponse(blob) {
  if (!blob) return blob
  // 检查 content-type 是否为 JSON
  const contentType = blob.type || ''
  if (contentType.includes('application/json')) {
    // 后端返回了 JSON 错误，需要解析
    try {
      const text = await blob.text()
      const errorData = JSON.parse(text)
      // 构造一个模拟的 axios 错误
      const error = new Error(errorData.message || '请求失败')
      error.response = {
        data: errorData,
        status: errorData.code || 500
      }
      throw error
    } catch (e) {
      // 如果 JSON 解析也失败，直接抛出原始错误
      if (e.response) throw e
      throw new Error('文件下载失败，服务器返回了无效的响应')
    }
  }
  return blob
}

// ==================== 请求重试机制 ====================

/**
 * 请求重试机制
 * @param {Function} requestFn - 请求函数
 * @param {Object} config - 请求配置
 * @param {number} [retryCount=0] - 当前重试次数
 * @returns {Promise} 请求结果
 */
async function requestWithRetry(requestFn, config, retryCount = 0) {
  try {
    return await requestFn(config)
  } catch (error) {
    const { retry } = DEFAULT_CONFIG

    // 检查是否为 AbortController 取消
    if (error.name === 'CanceledError' || error.name === 'AbortError') {
      return Promise.reject(error)
    }

    // 检查是否需要重试
    if (
      retryCount < retry.count &&
      retry.retryCondition(error)
    ) {
      // 延迟后重试
      await new Promise(resolve => setTimeout(resolve, retry.delay * (retryCount + 1)))
      return requestWithRetry(requestFn, config, retryCount + 1)
    }

    throw error
  }
}

// ==================== 请求拦截器 ====================

client.interceptors.request.use(
  (config) => {
    // 添加 Token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加请求标识（用于取消重复请求）
    if (config.cancelable !== false) {
      addPendingRequest(config)
    }

    // GET 请求缓存处理
    if (config.method === 'get') {
      if (config.cache === true) {
        // 启用缓存：先检查缓存
        const cacheKey = generateRequestKey(config)
        const cached = getCache(cacheKey)
        if (cached) {
          // 返回一个已 resolve 的 Promise，并标记来自缓存
          const source = new axios.CancelToken((cancel) => cancel({ __cached: true, data: cached }))
          config.cancelToken = source
        }
        // 记录缓存配置供响应拦截器使用
        config._cacheEnabled = true
        config._cacheTtl = config.cacheTtl || 60000
      } else if (config.responseType !== 'blob') {
        // 跳过 Blob 下载请求：_t 参数会触发广告拦截器（ERR_BLOCKED_BY_CLIENT）
        // 未启用缓存：添加时间戳防止浏览器缓存
        config.params = {
          ...config.params,
          _t: Date.now()
        }
      }
    }

    // 开发环境日志
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.params || config.data)
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ==================== 响应拦截器 ====================

client.interceptors.response.use(
  (response) => {
    // 从 pending 列表移除
    removePendingRequest(response.config)

    // 开发环境日志
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Response] ${response.config.url}`, response.data)
    }

    // GET 请求缓存写入
    if (
      response.config.method === 'get' &&
      response.config._cacheEnabled
    ) {
      const cacheKey = generateRequestKey(response.config)
      setCache(cacheKey, response.data, response.config._cacheTtl)
    }

    // 解包后端 ApiResponse 包装 { code, message, data }
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        return body.data
      }
      // 非零 code → 构造错误抛给错误拦截器
      const err = new Error(body.message || '请求失败')
      err.response = response
      return Promise.reject(err)
    }
    return body
  },
  (error) => {
    // 从 pending 列表移除
    if (error.config) {
      removePendingRequest(error.config)
    }

    // 处理请求取消（AbortController）
    if (axios.isCancel(error) || error.name === 'CanceledError' || error.name === 'AbortError') {
      // 如果是缓存命中导致的取消，返回缓存数据
      if (error.message?.__cached) {
        return error.message.data
      }
      console.log('[API] Request canceled:', error.message)
      return Promise.reject(error)
    }

    // 处理错误
    const errorInfo = ErrorHandler.parseError(error)

    // 认证错误特殊处理
    if (errorInfo.type === 'auth' && errorInfo.action === 'logout') {
      localStorage.removeItem('access_token')
      router.push('/login?expired=1')
    }

    // 开发环境日志
    if (process.env.NODE_ENV === 'development') {
      console.error('[API Error]', errorInfo)
    }

    return Promise.reject(error)
  }
)

// ==================== 封装 HTTP 方法 ====================

/**
 * GET 请求
 * @param {string} url - 请求地址
 * @param {Object} [params] - 查询参数
 * @param {Object} [config] - 额外配置
 * @param {boolean} [config.cache] - 是否启用缓存
 * @param {number} [config.cacheTtl] - 缓存过期时间（毫秒）
 * @returns {Promise} 请求结果
 */
export function get(url, params, config = {}) {
  return requestWithRetry(
    (cfg) => client.get(url, { ...cfg, params }),
    config
  )
}

/**
 * POST 请求
 * @param {string} url - 请求地址
 * @param {Object} [data] - 请求数据
 * @param {Object} [config] - 额外配置
 * @returns {Promise} 请求结果
 */
export function post(url, data, config = {}) {
  return requestWithRetry(
    (cfg) => client.post(url, data, cfg),
    config
  )
}

/**
 * PUT 请求
 * @param {string} url - 请求地址
 * @param {Object} [data] - 请求数据
 * @param {Object} [config] - 额外配置
 * @returns {Promise} 请求结果
 */
export function put(url, data, config = {}) {
  return requestWithRetry(
    (cfg) => client.put(url, data, cfg),
    config
  )
}

/**
 * DELETE 请求
 * @param {string} url - 请求地址
 * @param {Object} [config] - 额外配置
 * @returns {Promise} 请求结果
 */
export function del(url, config = {}) {
  return requestWithRetry(
    (cfg) => client.delete(url, cfg),
    config
  )
}

/**
 * PATCH 请求
 * @param {string} url - 请求地址
 * @param {Object} [data] - 请求数据
 * @param {Object} [config] - 额外配置
 * @returns {Promise} 请求结果
 */
export function patch(url, data, config = {}) {
  return requestWithRetry(
    (cfg) => client.patch(url, data, cfg),
    config
  )
}

/**
 * 上传文件
 * @param {string} url - 请求地址
 * @param {FormData} formData - 表单数据
 * @param {Function} [onProgress] - 进度回调
 * @param {Object} [config] - 额外配置
 * @returns {Promise} 请求结果
 */
export function upload(url, formData, onProgress, config = {}) {
  const uploadConfig = {
    ...config,
    headers: {
      ...(config.headers || {}),
      'Content-Type': 'multipart/form-data'
    },
    timeout: config.timeout || 120000, // 上传超时时间更长
    onUploadProgress: onProgress ? (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / (progressEvent.total || 1)
      )
      onProgress(percentCompleted)
    } : undefined
  }
  return requestWithRetry(
    (cfg) => client.post(url, formData, cfg),
    uploadConfig
  )
}

/**
 * 下载文件
 * 当响应是 JSON 错误（而非 blob）时，自动解析并抛出有意义的错误信息
 * @param {string} url - 请求地址
 * @param {Object} [config] - 额外配置
 * @returns {Promise<Blob>} 文件 Blob
 */
export async function download(url, config = {}) {
  const response = await client.get(url, {
    ...config,
    responseType: 'blob'
  })
  // 检查 blob 是否实际为 JSON 错误响应
  return parseBlobResponse(response)
}

// 导出 axios 实例供特殊场景使用
export default client
