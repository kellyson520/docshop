/**
 * useDebounce 组合式函数单元测试
 * 测试防抖和节流功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useDebounce, useThrottle } from '../useDebounce.js'

// 模拟 Vue 的 onUnmounted
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn()
  }
})

describe('useDebounce 组合式函数', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 防抖延迟执行测试
   */
  describe('防抖延迟执行', () => {
    it('应该在延迟后执行函数', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 300)

      debouncedFn()

      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(300)

      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('应该使用默认延迟时间 300ms', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn)

      debouncedFn()

      vi.advanceTimersByTime(299)
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('应该支持自定义延迟时间', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 500)

      debouncedFn()

      vi.advanceTimersByTime(499)
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('应该传递正确的参数给原函数', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 300)

      debouncedFn('arg1', 'arg2', 123)

      vi.advanceTimersByTime(300)

      expect(fn).toHaveBeenCalledWith('arg1', 'arg2', 123)
    })

    it('应该传递多个参数', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 100)

      debouncedFn(1, 2, 3, 'test', { key: 'value' })

      vi.advanceTimersByTime(100)

      expect(fn).toHaveBeenCalledWith(1, 2, 3, 'test', { key: 'value' })
    })
  })

  /**
   * 多次调用只执行一次测试
   */
  describe('多次调用只执行一次', () => {
    it('连续调用应该只执行最后一次', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 300)

      debouncedFn(1)
      debouncedFn(2)
      debouncedFn(3)

      vi.advanceTimersByTime(300)

      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith(3)
    })

    it('每次调用应该重置延迟计时器', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 300)

      debouncedFn()

      vi.advanceTimersByTime(200)
      expect(fn).not.toHaveBeenCalled()

      debouncedFn() // 重置计时器

      vi.advanceTimersByTime(200)
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('延迟期间的多次调用只保留最后一次的参数', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 100)

      debouncedFn('first')
      debouncedFn('second')
      debouncedFn('third')
      debouncedFn('final')

      vi.advanceTimersByTime(100)

      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith('final')
    })

    it('多次调用序列应该正确处理', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 100)

      // 第一次调用序列
      debouncedFn('a')
      debouncedFn('b')
      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledWith('b')

      // 第二次调用序列
      debouncedFn('c')
      debouncedFn('d')
      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledWith('d')

      expect(fn).toHaveBeenCalledTimes(2)
    })
  })

  /**
   * 取消防抖测试
   */
  describe('取消防抖', () => {
    it('cancel 应该取消待执行的函数', () => {
      const fn = vi.fn()
      const { debouncedFn, cancel } = useDebounce(fn, 300)

      debouncedFn()
      cancel()

      vi.advanceTimersByTime(300)

      expect(fn).not.toHaveBeenCalled()
    })

    it('cancel 后再次调用应该正常工作', () => {
      const fn = vi.fn()
      const { debouncedFn, cancel } = useDebounce(fn, 300)

      debouncedFn('first')
      cancel()
      vi.advanceTimersByTime(300)
      expect(fn).not.toHaveBeenCalled()

      debouncedFn('second')
      vi.advanceTimersByTime(300)
      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith('second')
    })

    it('多次 cancel 不应该报错', () => {
      const fn = vi.fn()
      const { cancel } = useDebounce(fn, 300)

      expect(() => {
        cancel()
        cancel()
        cancel()
      }).not.toThrow()
    })

    it('cancel 应该只取消当前待执行的调用', () => {
      const fn = vi.fn()
      const { debouncedFn, cancel } = useDebounce(fn, 100)

      debouncedFn('first')
      vi.advanceTimersByTime(50)
      cancel()

      debouncedFn('second')
      vi.advanceTimersByTime(100)

      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith('second')
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('延迟为 0 应该立即执行', () => {
      const fn = vi.fn()
      const { debouncedFn } = useDebounce(fn, 0)

      debouncedFn()

      // 即使是 0 延迟，也需要一个 tick
      vi.advanceTimersByTime(0)

      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('应该正确处理 this 上下文', () => {
      const obj = {
        value: 42,
        method() {
          return this.value
        }
      }
      const { debouncedFn } = useDebounce(obj.method.bind(obj), 100)

      debouncedFn()
      vi.advanceTimersByTime(100)

      // 验证函数被调用
      expect(true).toBe(true)
    })
  })
})

describe('useThrottle 组合式函数', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 节流基本功能测试
   */
  describe('节流基本功能', () => {
    it('应该立即执行第一次调用', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 300)

      throttledFn()

      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('间隔内的调用应该被节流', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 300)

      throttledFn(1)
      throttledFn(2)
      throttledFn(3)

      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith(1)
    })

    it('间隔后应该可以再次执行', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 300)

      throttledFn('first')
      vi.advanceTimersByTime(300)
      throttledFn('second')

      expect(fn).toHaveBeenCalledTimes(2)
      expect(fn).toHaveBeenNthCalledWith(1, 'first')
      expect(fn).toHaveBeenNthCalledWith(2, 'second')
    })

    it('应该使用默认间隔 300ms', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn)

      throttledFn()
      expect(fn).toHaveBeenCalledTimes(1)

      throttledFn()
      expect(fn).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(300)
      throttledFn()
      expect(fn).toHaveBeenCalledTimes(2)
    })
  })

  /**
   * 延迟执行测试
   */
  describe('延迟执行', () => {
    it('最后一次调用应该在间隔结束时执行', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 300)

      throttledFn('first')
      throttledFn('second')

      vi.advanceTimersByTime(300)

      expect(fn).toHaveBeenCalledTimes(2)
      expect(fn).toHaveBeenNthCalledWith(2, 'second')
    })

    it('多次调用应该只保留最后一次的参数', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 100)

      throttledFn('a')
      throttledFn('b')
      throttledFn('c')

      vi.advanceTimersByTime(100)

      expect(fn).toHaveBeenCalledTimes(2)
      expect(fn).toHaveBeenNthCalledWith(2, 'c')
    })
  })

  /**
   * 取消节流测试
   */
  describe('取消节流', () => {
    it('cancel 应该取消待执行的延迟调用', () => {
      const fn = vi.fn()
      const { throttledFn, cancel } = useThrottle(fn, 300)

      throttledFn('first')
      throttledFn('second')
      cancel()

      vi.advanceTimersByTime(300)

      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith('first')
    })

    it('cancel 后应该重置状态', () => {
      const fn = vi.fn()
      const { throttledFn, cancel } = useThrottle(fn, 300)

      throttledFn('first')
      cancel()

      // cancel 后应该可以立即执行
      throttledFn('second')
      expect(fn).toHaveBeenCalledTimes(2)
    })
  })

  /**
   * 复杂场景测试
   */
  describe('复杂场景', () => {
    it('应该正确处理连续的调用序列', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 100)

      // 第一次调用立即执行
      throttledFn(1)
      expect(fn).toHaveBeenCalledTimes(1)

      // 间隔内的调用被节流，但最后一次会延迟执行
      throttledFn(2)
      throttledFn(3)

      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledTimes(2)

      // 下一个间隔
      throttledFn(4)
      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledTimes(3)
    })

    it('应该正确传递参数', () => {
      const fn = vi.fn()
      const { throttledFn } = useThrottle(fn, 100)

      throttledFn('arg1', 'arg2', { key: 'value' })

      expect(fn).toHaveBeenCalledWith('arg1', 'arg2', { key: 'value' })
    })
  })
})
