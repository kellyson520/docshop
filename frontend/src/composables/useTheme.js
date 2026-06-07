import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

/**
 * 主题类型
 * @typedef {'light' | 'dark' | 'auto'} ThemeType
 */

/**
 * localStorage 存储键名
 */
const STORAGE_KEY = 'app_theme_preference'

/**
 * 媒体查询匹配器
 */
const mediaQuery = typeof window !== 'undefined'
  ? window.matchMedia('(prefers-color-scheme: dark)')
  : null

/**
 * 主题管理组合式函数
 * 提供主题切换、系统主题监听、主题持久化等功能
 *
 * @example
 * // 基础用法
 * const { theme, isDark, toggleTheme, setTheme } = useTheme()
 *
 * // 监听系统主题变化
 * const { followSystem, stopFollowingSystem } = useTheme({
 *   followSystem: true,
 *   onSystemThemeChange: (isDark) => console.log('系统主题变化:', isDark)
 * })
 *
 * @param {Object} options - 配置选项
 * @param {ThemeType} [options.defaultTheme='light'] - 默认主题
 * @param {boolean} [options.followSystem=false] - 是否跟随系统主题
 * @param {boolean} [options.persist=true] - 是否持久化主题偏好
 * @param {Function} [options.onThemeChange] - 主题变化回调
 * @param {Function} [options.onSystemThemeChange] - 系统主题变化回调
 * @returns {Object} 主题管理对象
 */
export function useTheme(options = {}) {
  const {
    defaultTheme = 'light',
    followSystem: initialFollowSystem = false,
    persist = true,
    onThemeChange,
    onSystemThemeChange
  } = options

  // 从 localStorage 读取保存的主题偏好
  const getSavedTheme = () => {
    if (!persist || typeof localStorage === 'undefined') return null
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        return parsed.theme || null
      }
    } catch (e) {
      console.warn('[useTheme] 读取主题偏好失败:', e)
    }
    return null
  }

  // 响应式状态
  const theme = ref(getSavedTheme() || defaultTheme)
  const followSystem = ref(initialFollowSystem)
  const systemIsDark = ref(mediaQuery?.matches || false)

  // 计算属性：当前是否为暗色模式
  const isDark = computed(() => {
    if (followSystem.value) {
      return systemIsDark.value
    }
    return theme.value === 'dark'
  })

  // 计算属性：当前主题标签
  const themeLabel = computed(() => {
    if (followSystem.value) return '跟随系统'
    return theme.value === 'dark' ? '暗色' : '亮色'
  })

  // 计算属性：主题图标
  const themeIcon = computed(() => {
    if (followSystem.value) return 'Monitor'
    return isDark.value ? 'Moon' : 'Sunny'
  })

  /**
   * 应用主题到 DOM
   * @private
   */
  const applyTheme = () => {
    if (typeof document === 'undefined') return

    const html = document.documentElement
    const currentTheme = followSystem.value
      ? (systemIsDark.value ? 'dark' : 'light')
      : theme.value

    html.setAttribute('data-theme', currentTheme)

    // 触发主题变化回调
    if (onThemeChange) {
      onThemeChange(currentTheme, isDark.value)
    }
  }

  /**
   * 保存主题偏好到 localStorage
   * @private
   */
  const saveTheme = () => {
    if (!persist || typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        theme: theme.value,
        followSystem: followSystem.value,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.warn('[useTheme] 保存主题偏好失败:', e)
    }
  }

  /**
   * 设置主题
   * @param {ThemeType} newTheme - 新主题
   */
  const setTheme = (newTheme) => {
    if (!['light', 'dark', 'auto'].includes(newTheme)) {
      console.warn(`[useTheme] 不支持的主题: ${newTheme}`)
      return
    }

    if (newTheme === 'auto') {
      followSystem.value = true
    } else {
      followSystem.value = false
      theme.value = newTheme
    }

    applyTheme()
    saveTheme()
  }

  /**
   * 切换主题（亮色/暗色）
   */
  const toggleTheme = () => {
    if (followSystem.value) {
      // 如果正在跟随系统，切换到相反的手动主题
      followSystem.value = false
      theme.value = systemIsDark.value ? 'light' : 'dark'
    } else {
      theme.value = theme.value === 'dark' ? 'light' : 'dark'
    }

    applyTheme()
    saveTheme()
  }

  /**
   * 切换到亮色主题
   */
  const setLightTheme = () => {
    setTheme('light')
  }

  /**
   * 切换到暗色主题
   */
  const setDarkTheme = () => {
    setTheme('dark')
  }

  /**
   * 跟随系统主题
   */
  const followSystemTheme = () => {
    followSystem.value = true
    applyTheme()
    saveTheme()
  }

  /**
   * 停止跟随系统主题
   */
  const stopFollowingSystem = () => {
    followSystem.value = false
    theme.value = systemIsDark.value ? 'dark' : 'light'
    applyTheme()
    saveTheme()
  }

  /**
   * 系统主题变化处理函数
   * @private
   */
  const handleSystemThemeChange = (event) => {
    systemIsDark.value = event.matches

    if (onSystemThemeChange) {
      onSystemThemeChange(event.matches)
    }

    if (followSystem.value) {
      applyTheme()
    }
  }

  /**
   * 重置主题为默认值
   */
  const resetTheme = () => {
    theme.value = defaultTheme
    followSystem.value = initialFollowSystem
    applyTheme()
    saveTheme()
  }

  // 监听主题变化
  watch([theme, followSystem, systemIsDark], () => {
    applyTheme()
  }, { immediate: true })

  // 生命周期钩子
  onMounted(() => {
    if (mediaQuery) {
      // 初始化系统主题状态
      systemIsDark.value = mediaQuery.matches

      // 监听系统主题变化
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleSystemThemeChange)
      } else {
        // 兼容旧版浏览器
        mediaQuery.addListener(handleSystemThemeChange)
      }
    }

    // 初始应用主题
    applyTheme()
  })

  onUnmounted(() => {
    if (mediaQuery) {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleSystemThemeChange)
      } else {
        // 兼容旧版浏览器
        mediaQuery.removeListener(handleSystemThemeChange)
      }
    }
  })

  return {
    // 状态
    theme,
    isDark,
    followSystem,
    systemIsDark,
    themeLabel,
    themeIcon,

    // 方法
    setTheme,
    toggleTheme,
    setLightTheme,
    setDarkTheme,
    followSystemTheme,
    stopFollowingSystem,
    resetTheme
  }
}

/**
 * 获取当前系统主题
 * @returns {boolean} 是否为暗色模式
 */
export function getSystemTheme() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * 监听系统主题变化
 * @param {Function} callback - 回调函数，接收 isDark 参数
 * @returns {Function} 取消监听的函数
 */
export function watchSystemTheme(callback) {
  if (typeof window === 'undefined') return () => {}

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

  const handler = (event) => {
    callback(event.matches)
  }

  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handler)
  } else {
    mediaQuery.addListener(handler)
  }

  // 立即执行一次回调
  callback(mediaQuery.matches)

  // 返回取消监听的函数
  return () => {
    if (mediaQuery.removeEventListener) {
      mediaQuery.removeEventListener('change', handler)
    } else {
      mediaQuery.removeListener(handler)
    }
  }
}

/**
 * 应用主题到 DOM（全局函数）
 * @param {ThemeType} theme - 主题类型
 */
export function applyThemeToDOM(theme) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
}

export default useTheme
