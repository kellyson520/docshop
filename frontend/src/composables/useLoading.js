/**
 * 加载状态管理组合式函数
 * 提供统一的加载状态管理，支持单区域和多区域加载状态
 */

import { ref, computed } from 'vue'

/**
 * 单区域加载状态管理
 * @param {boolean} [initialState=false] - 初始加载状态
 * @returns {Object} 加载状态及相关方法
 */
export function useLoading(initialState = false) {
  // 加载状态
  const loading = ref(initialState)
  // 加载提示文本
  const loadingText = ref('')
  // 加载进度（0-100）
  const progress = ref(0)

  /**
   * 开始加载
   * @param {string} [text=''] - 加载提示文本
   */
  const start = (text = '') => {
    loading.value = true
    loadingText.value = text
    progress.value = 0
  }

  /**
   * 更新加载进度
   * @param {number} value - 进度值（0-100）
   */
  const updateProgress = (value) => {
    progress.value = Math.min(100, Math.max(0, value))
  }

  /**
   * 停止加载
   */
  const stop = () => {
    loading.value = false
    loadingText.value = ''
    progress.value = 0
  }

  return {
    // 使用 computed 包装，防止外部直接修改
    loading: computed(() => loading.value),
    loadingText: computed(() => loadingText.value),
    progress: computed(() => progress.value),
    start,
    updateProgress,
    stop
  }
}

/**
 * 多区域加载状态管理
 * 适用于页面中有多个独立加载区域的场景
 * @param {string[]} [zones=[]] - 加载区域标识列表
 * @returns {Object} 多区域加载状态及相关方法
 * @example
 * const { states, start, stop, isLoading } = useMultiLoading(['list', 'form', 'detail'])
 * start('list', '加载列表中...')
 * stop('list')
 */
export function useMultiLoading(zones = []) {
  // 初始化各区域的加载状态
  const states = ref(
    zones.reduce((acc, zone) => {
      acc[zone] = { loading: false, text: '', progress: 0 }
      return acc
    }, {})
  )

  /**
   * 开始指定区域的加载
   * @param {string} zone - 区域标识
   * @param {string} [text=''] - 加载提示文本
   */
  const start = (zone, text = '') => {
    if (states.value[zone]) {
      states.value[zone].loading = true
      states.value[zone].text = text
    }
  }

  /**
   * 更新指定区域的加载进度
   * @param {string} zone - 区域标识
   * @param {number} value - 进度值（0-100）
   */
  const updateProgress = (zone, value) => {
    if (states.value[zone]) {
      states.value[zone].progress = Math.min(100, Math.max(0, value))
    }
  }

  /**
   * 停止指定区域的加载
   * @param {string} zone - 区域标识
   */
  const stop = (zone) => {
    if (states.value[zone]) {
      states.value[zone].loading = false
      states.value[zone].text = ''
      states.value[zone].progress = 0
    }
  }

  /**
   * 停止所有区域的加载
   */
  const stopAll = () => {
    Object.keys(states.value).forEach((zone) => {
      stop(zone)
    })
  }

  /**
   * 检查指定区域是否正在加载
   * @param {string} zone - 区域标识
   * @returns {boolean}
   */
  const isLoading = (zone) => states.value[zone]?.loading || false

  /**
   * 检查是否有任何区域正在加载
   * @returns {boolean}
   */
  const isAnyLoading = computed(() => {
    return Object.values(states.value).some((state) => state.loading)
  })

  /**
   * 添加新的加载区域
   * @param {string} zone - 区域标识
   */
  const addZone = (zone) => {
    if (!states.value[zone]) {
      states.value[zone] = { loading: false, text: '', progress: 0 }
    }
  }

  /**
   * 移除加载区域
   * @param {string} zone - 区域标识
   */
  const removeZone = (zone) => {
    if (states.value[zone]) {
      delete states.value[zone]
    }
  }

  return {
    states: computed(() => states.value),
    isAnyLoading,
    start,
    updateProgress,
    stop,
    stopAll,
    isLoading,
    addZone,
    removeZone
  }
}

/**
 * 带超时控制的加载状态
 * 适用于需要防止加载状态无限持续的场景
 * @param {Object} [options={}] - 配置选项
 * @param {number} [options.timeout=30000] - 超时时间（毫秒）
 * @param {Function} [options.onTimeout] - 超时回调
 * @returns {Object} 加载状态及相关方法
 */
export function useLoadingWithTimeout(options = {}) {
  const { timeout = 30000, onTimeout } = options
  const { loading, loadingText, start, stop } = useLoading()
  
  let timeoutId = null

  const startWithTimeout = (text = '') => {
    start(text)
    
    // 清除之前的定时器
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    
    // 设置超时定时器
    timeoutId = setTimeout(() => {
      stop()
      if (typeof onTimeout === 'function') {
        onTimeout()
      }
    }, timeout)
  }

  const stopWithTimeout = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    stop()
  }

  return {
    loading,
    loadingText,
    start: startWithTimeout,
    stop: stopWithTimeout
  }
}

export default useLoading