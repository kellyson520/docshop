/**
 * 响应式工具组合式函数
 * 提供设备类型检测和响应式布局支持
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * 断点配置（像素值）
 */
const BREAKPOINTS = {
  xs: 0,      // 超小屏幕（手机）
  sm: 576,    // 小屏幕（大手机）
  md: 768,    // 中等屏幕（平板）
  lg: 992,    // 大屏幕（桌面）
  xl: 1200,   // 超大屏幕（大桌面）
  xxl: 1400   // 超超大屏幕
}

/**
 * 使用响应式布局
 * @param {Object} [options={}] - 配置选项
 * @param {Object} [options.breakpoints] - 自定义断点
 * @returns {Object} 响应式状态和方法
 */
export function useResponsive(options = {}) {
  const breakpoints = { ...BREAKPOINTS, ...options.breakpoints }
  
  // 当前视口宽度
  const width = ref(0)
  // 当前视口高度
  const height = ref(0)

  /**
   * 设备类型判断
   */
  const isMobile = computed(() => width.value < breakpoints.md)
  const isTablet = computed(() => width.value >= breakpoints.md && width.value < breakpoints.lg)
  const isDesktop = computed(() => width.value >= breakpoints.lg)
  const isLargeDesktop = computed(() => width.value >= breakpoints.xl)

  /**
   * 断点判断
   */
  const isXs = computed(() => width.value < breakpoints.sm)
  const isSm = computed(() => width.value >= breakpoints.sm && width.value < breakpoints.md)
  const isMd = computed(() => width.value >= breakpoints.md && width.value < breakpoints.lg)
  const isLg = computed(() => width.value >= breakpoints.lg && width.value < breakpoints.xl)
  const isXl = computed(() => width.value >= breakpoints.xl && width.value < breakpoints.xxl)
  const isXxl = computed(() => width.value >= breakpoints.xxl)

  /**
   * 当前断点名称
   */
  const currentBreakpoint = computed(() => {
    if (isXxl.value) return 'xxl'
    if (isXl.value) return 'xl'
    if (isLg.value) return 'lg'
    if (isMd.value) return 'md'
    if (isSm.value) return 'sm'
    return 'xs'
  })

  /**
   * 屏幕方向
   */
  const isPortrait = computed(() => height.value > width.value)
  const isLandscape = computed(() => width.value > height.value)

  /**
   * 更新尺寸信息
   */
  const updateSize = () => {
    width.value = window.innerWidth
    height.value = window.innerHeight
  }

  /**
   * 检查是否大于指定断点
   * @param {string} breakpoint - 断点名称
   * @returns {boolean}
   */
  const up = (breakpoint) => {
    return width.value >= (breakpoints[breakpoint] || 0)
  }

  /**
   * 检查是否小于指定断点
   * @param {string} breakpoint - 断点名称
   * @returns {boolean}
   */
  const down = (breakpoint) => {
    return width.value < (breakpoints[breakpoint] || Infinity)
  }

  /**
   * 检查是否在指定断点范围内
   * @param {string} min - 最小断点
   * @param {string} max - 最大断点
   * @returns {boolean}
   */
  const between = (min, max) => {
    return up(min) && down(max)
  }

  // 监听窗口大小变化
  let resizeObserver = null

  onMounted(() => {
    // 初始化尺寸
    updateSize()

    // 使用 ResizeObserver 或 fallback 到 resize 事件
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(updateSize)
      resizeObserver.observe(document.documentElement)
    } else {
      window.addEventListener('resize', updateSize)
    }
  })

  onUnmounted(() => {
    if (resizeObserver) {
      resizeObserver.disconnect()
    } else {
      window.removeEventListener('resize', updateSize)
    }
  })

  return {
    // 尺寸信息
    width: computed(() => width.value),
    height: computed(() => height.value),
    
    // 设备类型
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    
    // 断点判断
    isXs,
    isSm,
    isMd,
    isLg,
    isXl,
    isXxl,
    currentBreakpoint,
    
    // 屏幕方向
    isPortrait,
    isLandscape,
    
    // 方法
    up,
    down,
    between,
    updateSize
  }
}

/**
 * 使用媒体查询
 * @param {string} query - CSS 媒体查询字符串
 * @returns {Ref<boolean>} 是否匹配
 */
export function useMediaQuery(query) {
  const matches = ref(false)
  let mediaQueryList = null

  const updateMatch = () => {
    if (mediaQueryList) {
      matches.value = mediaQueryList.matches
    }
  }

  onMounted(() => {
    if (window.matchMedia) {
      mediaQueryList = window.matchMedia(query)
      matches.value = mediaQueryList.matches
      
      // 监听变化
      if (mediaQueryList.addEventListener) {
        mediaQueryList.addEventListener('change', updateMatch)
      } else {
        // 兼容旧版 Safari
        mediaQueryList.addListener(updateMatch)
      }
    }
  })

  onUnmounted(() => {
    if (mediaQueryList) {
      if (mediaQueryList.removeEventListener) {
        mediaQueryList.removeEventListener('change', updateMatch)
      } else {
        mediaQueryList.removeListener(updateMatch)
      }
    }
  })

  return matches
}

/**
 * 使用 prefers-reduced-motion 媒体查询
 * @returns {Ref<boolean>} 用户是否偏好减少动画
 */
export function usePrefersReducedMotion() {
  return useMediaQuery('(prefers-reduced-motion: reduce)')
}

/**
 * 使用 prefers-color-scheme 媒体查询
 * @returns {Ref<boolean>} 是否为暗色模式
 */
export function usePrefersDarkMode() {
  return useMediaQuery('(prefers-color-scheme: dark)')
}

/**
 * 使用悬停能力检测
 * @returns {Ref<boolean>} 设备是否支持悬停
 */
export function useHoverCapability() {
  return useMediaQuery('(hover: hover)')
}

/**
 * 使用指针精度检测
 * @returns {Ref<boolean>} 是否为精确指针（鼠标）
 */
export function useFinePointer() {
  return useMediaQuery('(pointer: fine)')
}

export default useResponsive