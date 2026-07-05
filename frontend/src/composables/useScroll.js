import { ref, computed, onMounted, onUnmounted } from 'vue'

function toNumber(value) {
  const normalized = Number(value)
  return Number.isFinite(normalized) ? normalized : 0
}

function getScrollableDistance(element) {
  if (!element) return 0
  return Math.max(0, toNumber(element.scrollHeight) - toNumber(element.clientHeight))
}

export function getDocumentScrollElement(doc = typeof document !== 'undefined' ? document : null) {
  if (!doc) return null

  const candidates = [doc.body, doc.scrollingElement, doc.documentElement].filter(Boolean)

  return candidates.find((element) => (
    toNumber(element.scrollTop) > 0 || getScrollableDistance(element) > 0
  )) || doc.scrollingElement || doc.documentElement || doc.body || null
}

export function getWindowScrollPosition(
  win = typeof window !== 'undefined' ? window : null,
  doc = typeof document !== 'undefined' ? document : null,
) {
  if (!doc) return { x: 0, y: 0 }

  const root = getDocumentScrollElement(doc)

  return {
    x: Math.max(
      toNumber(win?.pageXOffset),
      toNumber(root?.scrollLeft),
      toNumber(doc.documentElement?.scrollLeft),
      toNumber(doc.body?.scrollLeft),
    ),
    y: Math.max(
      toNumber(win?.pageYOffset),
      toNumber(root?.scrollTop),
      toNumber(doc.documentElement?.scrollTop),
      toNumber(doc.body?.scrollTop),
    ),
  }
}

export function scrollDocumentTo(
  win = typeof window !== 'undefined' ? window : null,
  doc = typeof document !== 'undefined' ? document : null,
  x = 0,
  y = 0,
  behavior = 'smooth',
) {
  if (!doc) return

  const root = getDocumentScrollElement(doc)

  if (root && typeof root.scrollTo === 'function') {
    root.scrollTo({ left: x, top: y, behavior })
  } else if (root) {
    root.scrollLeft = x
    root.scrollTop = y
  }

  if (doc.documentElement && doc.documentElement !== root) {
    doc.documentElement.scrollLeft = x
    doc.documentElement.scrollTop = y
  }

  if (doc.body && doc.body !== root) {
    doc.body.scrollLeft = x
    doc.body.scrollTop = y
  }

  if (win && typeof win.scrollTo === 'function') {
    win.scrollTo({ left: x, top: y, behavior })
  }
}

export function getElementDocumentScrollTop(
  element,
  win = typeof window !== 'undefined' ? window : null,
  doc = typeof document !== 'undefined' ? document : null,
  offset = 0,
) {
  if (!element) return 0

  const rect = element.getBoundingClientRect()
  const { y } = getWindowScrollPosition(win, doc)
  return y + toNumber(rect?.top) + toNumber(offset)
}

/**
 * 滚动位置对象
 * @typedef {Object} ScrollPosition
 * @property {number} x - 水平滚动位置
 * @property {number} y - 垂直滚动位置
 */

/**
 * 滚动方向
 * @typedef {'up' | 'down' | 'left' | 'right' | 'none'} ScrollDirection
 */

/**
 * 滚动管理组合式函数
 * 提供滚动位置监听、滚动方向判断、平滑滚动等功能
 *
 * @example
 * // 基础用法
 * const { scrollY, isScrolled, scrollToTop } = useScroll()
 *
 * // 监听滚动方向
 * const { scrollDirection, isScrollingUp, isScrollingDown } = useScroll()
 *
 * // 滚动到指定元素
 * const { scrollToElement } = useScroll()
 * scrollToElement('#target', { behavior: 'smooth', offset: -64 })
 *
 * @param {Object} options - 配置选项
 * @param {number} [options.threshold=50] - 判断已滚动的阈值（像素）
 * @param {boolean} [options.throttle=true] - 是否启用节流
 * @param {number} [options.throttleWait=16] - 节流等待时间（毫秒，默认约60fps）
 * @param {Function} [options.onScroll] - 滚动回调函数
 * @param {Function} [options.onScrollUp] - 向上滚动回调
 * @param {Function} [options.onScrollDown] - 向下滚动回调
 * @param {Function} [options.onReachTop] - 滚动到顶部回调
 * @param {Function} [options.onReachBottom] - 滚动到底部回调
 * @returns {Object} 滚动管理对象
 */
export function useScroll(options = {}) {
  const {
    threshold = 50,
    throttle = true,
    throttleWait = 16,
    onScroll,
    onScrollUp,
    onScrollDown,
    onReachTop,
    onReachBottom
  } = options

  // 响应式状态
  const scrollX = ref(0)
  const scrollY = ref(0)
  const lastScrollX = ref(0)
  const lastScrollY = ref(0)
  const scrollDirection = ref('none')
  const isScrolling = ref(false)
  let scrollTimeout = null
  let hasReachedBottom = false

  // 计算属性
  const isScrolled = computed(() => scrollY.value > threshold)
  const isAtTop = computed(() => scrollY.value <= 0)
  const isAtBottom = computed(() => {
    if (typeof window === 'undefined') return false
    const scrollRoot = getDocumentScrollElement(document)
    const docHeight = toNumber(scrollRoot?.scrollHeight)
    const viewportHeight = toNumber(scrollRoot?.clientHeight) || toNumber(window.innerHeight)
    return scrollY.value + viewportHeight >= docHeight - 10
  })
  const isScrollingUp = computed(() => scrollDirection.value === 'up')
  const isScrollingDown = computed(() => scrollDirection.value === 'down')
  const scrollProgress = computed(() => {
    if (typeof window === 'undefined') return 0
    const scrollRoot = getDocumentScrollElement(document)
    const docHeight = toNumber(scrollRoot?.scrollHeight) - (
      toNumber(scrollRoot?.clientHeight) || toNumber(window.innerHeight)
    )
    if (docHeight <= 0) return 0
    return Math.min(100, Math.max(0, (scrollY.value / docHeight) * 100))
  })

  /**
   * 节流函数
   * @private
   */
  function throttleFn(fn, wait) {
    let lastTime = 0
    return function (...args) {
      const now = Date.now()
      if (now - lastTime >= wait) {
        lastTime = now
        fn.apply(this, args)
      }
    }
  }

  /**
   * 处理滚动事件
   * @private
   */
  const handleScroll = () => {
    if (typeof window === 'undefined') return

    const { x: currentX, y: currentY } = getWindowScrollPosition(window, document)

    // 更新滚动位置
    scrollX.value = currentX
    scrollY.value = currentY

    // 判断滚动方向
    if (currentY > lastScrollY.value) {
      scrollDirection.value = 'down'
      if (onScrollDown) onScrollDown()
    } else if (currentY < lastScrollY.value) {
      scrollDirection.value = 'up'
      if (onScrollUp) onScrollUp()
    }

    // 判断是否滚动到顶部/底部
    if (currentY <= 0 && onReachTop) {
      onReachTop()
    }
    if (isAtBottom.value && onReachBottom && !hasReachedBottom) {
      hasReachedBottom = true
      onReachBottom()
    }
    if (!isAtBottom.value) {
      hasReachedBottom = false
    }

    // 更新上次滚动位置
    lastScrollX.value = currentX
    lastScrollY.value = currentY

    // 设置滚动状态
    isScrolling.value = true
    clearTimeout(scrollTimeout)
    scrollTimeout = setTimeout(() => {
      isScrolling.value = false
    }, 150)

    // 触发滚动回调
    if (onScroll) {
      onScroll({ x: currentX, y: currentY, direction: scrollDirection.value })
    }
  }

  /**
   * 滚动到指定位置
   * @param {number} x - 水平位置
   * @param {number} y - 垂直位置
   * @param {ScrollBehavior} [behavior='smooth'] - 滚动行为
   */
  const scrollTo = (x, y, behavior = 'smooth') => {
    if (typeof window === 'undefined') return
    scrollDocumentTo(window, document, x, y, behavior)
  }

  /**
   * 滚动到顶部
   * @param {ScrollBehavior} [behavior='smooth'] - 滚动行为
   */
  const scrollToTop = (behavior = 'smooth') => {
    scrollTo(0, 0, behavior)
  }

  /**
   * 滚动到底部
   * @param {ScrollBehavior} [behavior='smooth'] - 滚动行为
   */
  const scrollToBottom = (behavior = 'smooth') => {
    if (typeof window === 'undefined') return
    const scrollRoot = getDocumentScrollElement(document)
    const docHeight = toNumber(scrollRoot?.scrollHeight) || toNumber(document.documentElement.scrollHeight)
    scrollTo(0, docHeight, behavior)
  }

  /**
   * 滚动到指定元素
   * @param {string|Element} target - 目标元素选择器或元素
   * @param {Object} [options={}] - 配置选项
   * @param {ScrollBehavior} [options.behavior='smooth'] - 滚动行为
   * @param {number} [options.offset=0] - 偏移量（像素）
   * @param {string} [options.block='start'] - 垂直对齐方式
   * @param {string} [options.inline='nearest'] - 水平对齐方式
   */
  const scrollToElement = (target, options = {}) => {
    const {
      behavior = 'smooth',
      offset = 0,
      block = 'start',
      inline = 'nearest'
    } = options

    if (typeof window === 'undefined') return

    let element
    if (typeof target === 'string') {
      element = document.querySelector(target)
    } else {
      element = target
    }

    if (!element) {
      console.warn(`[useScroll] 未找到目标元素: ${target}`)
      return
    }

    // 计算位置并应用偏移
    const scrollTop = getElementDocumentScrollTop(element, window, document, offset)

    scrollTo(0, scrollTop, behavior)
  }

  /**
   * 滚动到指定元素（使用原生 scrollIntoView）
   * @param {string|Element} target - 目标元素选择器或元素
   * @param {Object} [options={}] - 配置选项
   */
  const scrollIntoView = (target, options = {}) => {
    const {
      behavior = 'smooth',
      block = 'start',
      inline = 'nearest'
    } = options

    if (typeof window === 'undefined') return

    let element
    if (typeof target === 'string') {
      element = document.querySelector(target)
    } else {
      element = target
    }

    if (!element) {
      console.warn(`[useScroll] 未找到目标元素: ${target}`)
      return
    }

    element.scrollIntoView({ behavior, block, inline })
  }

  /**
   * 锁定/解锁页面滚动
   * @param {boolean} locked - 是否锁定
   */
  const setScrollLock = (locked) => {
    if (typeof document === 'undefined') return

    const body = document.body
    if (locked) {
      const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth
      body.style.overflow = 'hidden'
      body.style.paddingRight = `${scrollBarWidth}px`
    } else {
      body.style.overflow = ''
      body.style.paddingRight = ''
    }
  }

  /**
   * 获取元素在视口中的位置
   * @param {string|Element} target - 目标元素
   * @returns {Object|null} 位置信息
   */
  const getElementPosition = (target) => {
    if (typeof window === 'undefined') return null

    let element
    if (typeof target === 'string') {
      element = document.querySelector(target)
    } else {
      element = target
    }

    if (!element) return null

    const rect = element.getBoundingClientRect()
    return {
      top: rect.top,
      left: rect.left,
      bottom: rect.bottom,
      right: rect.right,
      width: rect.width,
      height: rect.height,
      inViewport: rect.top >= 0 && rect.bottom <= window.innerHeight
    }
  }

  /**
   * 监听元素进入视口
   * @param {string|Element} target - 目标元素
   * @param {Function} callback - 回调函数
   * @param {Object} [options={}] - IntersectionObserver 选项
   * @returns {Function} 取消监听的函数
   */
  const watchElementInViewport = (target, callback, options = {}) => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      return () => {}
    }

    let element
    if (typeof target === 'string') {
      element = document.querySelector(target)
    } else {
      element = target
    }

    if (!element) {
      console.warn(`[useScroll] 未找到目标元素: ${target}`)
      return () => {}
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        callback(entry.isIntersecting, entry)
      })
    }, {
      threshold: 0,
      rootMargin: '0px',
      ...options
    })

    observer.observe(element)

    return () => {
      observer.unobserve(element)
      observer.disconnect()
    }
  }

  // 生命周期钩子
  onMounted(() => {
    if (typeof window === 'undefined') return

    // 初始化滚动位置
    const initialPosition = getWindowScrollPosition(window, document)
    scrollX.value = initialPosition.x
    scrollY.value = initialPosition.y
    lastScrollX.value = scrollX.value
    lastScrollY.value = scrollY.value

    // 添加滚动监听
    const scrollHandler = throttle
      ? throttleFn(handleScroll, throttleWait)
      : handleScroll

    window.addEventListener('scroll', scrollHandler, { passive: true })

    // 保存清理函数
    const cleanup = () => {
      window.removeEventListener('scroll', scrollHandler)
      clearTimeout(scrollTimeout)
    }

    // 在组件卸载时清理
    onUnmounted(cleanup)
  })

  return {
    // 状态
    scrollX,
    scrollY,
    scrollDirection,
    isScrolling,

    // 计算属性
    isScrolled,
    isAtTop,
    isAtBottom,
    isScrollingUp,
    isScrollingDown,
    scrollProgress,

    // 方法
    scrollTo,
    scrollToTop,
    scrollToBottom,
    scrollToElement,
    scrollIntoView,
    setScrollLock,
    getElementPosition,
    watchElementInViewport
  }
}

/**
 * 创建平滑滚动锚点链接
 * @param {string} selector - 锚点选择器
 * @param {Object} [options={}] - 配置选项
 * @returns {Function} 点击处理函数
 */
export function createAnchorLink(selector, options = {}) {
  const { offset = -64, behavior = 'smooth' } = options

  return (event) => {
    if (event) {
      event.preventDefault()
    }

    if (typeof document === 'undefined') return

    const element = document.querySelector(selector)
    if (element) {
      const scrollTop = getElementDocumentScrollTop(element, window, document, offset)
      scrollDocumentTo(window, document, 0, scrollTop, behavior)
    }
  }
}

/**
 * 防抖滚动处理
 * @param {Function} callback - 回调函数
 * @param {number} [wait=100] - 等待时间
 * @returns {Function} 防抖处理后的函数
 */
export function debounceScroll(callback, wait = 100) {
  let timeout
  return function (...args) {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      callback.apply(this, args)
    }, wait)
  }
}

/**
 * 节流滚动处理
 * @param {Function} callback - 回调函数
 * @param {number} [wait=16] - 等待时间
 * @returns {Function} 节流处理后的函数
 */
export function throttleScroll(callback, wait = 16) {
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= wait) {
      lastTime = now
      callback.apply(this, args)
    }
  }
}

/**
 * 监听滚动停止
 * @param {Function} callback - 回调函数
 * @param {number} [wait=150] - 等待时间
 * @returns {Function} 取消监听的函数
 */
export function onScrollStop(callback, wait = 150) {
  if (typeof window === 'undefined') return () => {}

  let timeout

  const handler = () => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      callback()
    }, wait)
  }

  window.addEventListener('scroll', handler, { passive: true })

  return () => {
    window.removeEventListener('scroll', handler)
    clearTimeout(timeout)
  }
}

export default useScroll
