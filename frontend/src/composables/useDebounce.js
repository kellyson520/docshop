/**
 * 防抖和节流组合式函数
 * 自动在组件卸载时清理定时器，防止内存泄漏
 */

import { onUnmounted } from 'vue'

/**
 * 防抖函数
 * 在连续触发事件时，只在最后一次触发后的指定延迟时间后执行回调
 *
 * @param {Function} fn - 需要防抖的函数
 * @param {number} [delay=300] - 延迟时间（毫秒）
 * @returns {Function} 防抖后的函数
 *
 * @example
 * const { debouncedFn, cancel } = useDebounce(() => {
 *   console.log('搜索:', searchValue.value)
 * }, 500)
 */
export function useDebounce(fn, delay = 300) {
  let timer = null

  /**
   * 防抖后的函数
   * @param  {...any} args - 传递给原函数的参数
   */
  const debouncedFn = (...args) => {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      fn(...args)
      timer = null
    }, delay)
  }

  /**
   * 取消待执行的防抖调用
   */
  const cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  // 组件卸载时自动清理
  onUnmounted(() => {
    cancel()
  })

  return { debouncedFn, cancel }
}

/**
 * 节流函数
 * 在连续触发事件时，保证在指定时间间隔内只执行一次回调
 *
 * @param {Function} fn - 需要节流的函数
 * @param {number} [interval=300] - 时间间隔（毫秒）
 * @returns {Function} 节流后的函数
 *
 * @example
 * const { throttledFn, cancel } = useThrottle(() => {
 *   console.log('滚动位置:', window.scrollY)
 * }, 200)
 */
export function useThrottle(fn, interval = 300) {
  let timer = null
  let lastExecTime = 0
  let latestArgs = null

  /**
   * 节流后的函数
   * @param  {...any} args - 传递给原函数的参数
   */
  const throttledFn = (...args) => {
    const now = Date.now()
    const remaining = interval - (now - lastExecTime)
    latestArgs = args

    if (remaining <= 0) {
      // 立即执行
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      lastExecTime = now
      fn(...args)
      latestArgs = null
    } else if (!timer) {
      // 延迟到间隔结束时执行
      timer = setTimeout(() => {
        timer = null
        const invokeArgs = latestArgs || args
        latestArgs = null
        fn(...invokeArgs)
        lastExecTime = Date.now()
      }, remaining)
    }
  }

  /**
   * 取消待执行的节流调用
   */
  const cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    latestArgs = null
    lastExecTime = 0
  }

  // 组件卸载时自动清理
  onUnmounted(() => {
    cancel()
  })

  return { throttledFn, cancel }
}

export default useDebounce
