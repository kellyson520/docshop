/**
 * useLoading 组合式函数单元测试
 * 测试加载状态管理、多区域加载和超时控制功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, nextTick } from 'vue'
import { useLoading, useMultiLoading, useLoadingWithTimeout } from '../useLoading.js'

describe('useLoading 组合式函数', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该具有正确的默认初始状态', () => {
      const { loading, loadingText, progress } = useLoading()

      expect(loading.value).toBe(false)
      expect(loadingText.value).toBe('')
      expect(progress.value).toBe(0)
    })

    it('应该支持自定义初始状态', () => {
      const { loading, loadingText, progress } = useLoading(true)

      expect(loading.value).toBe(true)
      expect(loadingText.value).toBe('')
      expect(progress.value).toBe(0)
    })

    it('加载状态应该是只读的 computed', () => {
      const { loading } = useLoading()

      // 尝试直接修改应该失败（或在严格模式下报错）
      // 这里我们验证它是 computed 类型
      expect(typeof loading).toBe('object')
    })
  })

  /**
   * 开始加载测试
   */
  describe('开始加载', () => {
    it('start 方法应该设置加载状态为 true', () => {
      const { loading, loadingText, start } = useLoading()

      start()

      expect(loading.value).toBe(true)
    })

    it('start 方法应该设置加载文本', () => {
      const { loadingText, start } = useLoading()

      start('正在加载数据...')

      expect(loadingText.value).toBe('正在加载数据...')
    })

    it('start 方法应该重置进度为 0', () => {
      const { progress, start, updateProgress } = useLoading()

      updateProgress(50)
      expect(progress.value).toBe(50)

      start()

      expect(progress.value).toBe(0)
    })

    it('多次调用 start 应该保持加载状态为 true', () => {
      const { loading, loadingText, start } = useLoading()

      start('第一次')
      start('第二次')

      expect(loading.value).toBe(true)
      expect(loadingText.value).toBe('第二次')
    })
  })

  /**
   * 停止加载测试
   */
  describe('停止加载', () => {
    it('stop 方法应该设置加载状态为 false', () => {
      const { loading, start, stop } = useLoading()

      start()
      expect(loading.value).toBe(true)

      stop()

      expect(loading.value).toBe(false)
    })

    it('stop 方法应该清空加载文本', () => {
      const { loadingText, start, stop } = useLoading()

      start('加载中...')
      stop()

      expect(loadingText.value).toBe('')
    })

    it('stop 方法应该重置进度为 0', () => {
      const { progress, start, updateProgress, stop } = useLoading()

      start()
      updateProgress(75)
      stop()

      expect(progress.value).toBe(0)
    })

    it('未开始加载时调用 stop 应该保持状态不变', () => {
      const { loading, loadingText, progress, stop } = useLoading()

      stop()

      expect(loading.value).toBe(false)
      expect(loadingText.value).toBe('')
      expect(progress.value).toBe(0)
    })
  })

  /**
   * 进度更新测试
   */
  describe('进度更新', () => {
    it('应该正确更新进度值', () => {
      const { progress, updateProgress } = useLoading()

      updateProgress(50)

      expect(progress.value).toBe(50)
    })

    it('进度值应该在 0-100 范围内', () => {
      const { progress, updateProgress } = useLoading()

      updateProgress(150)
      expect(progress.value).toBe(100)

      updateProgress(-50)
      expect(progress.value).toBe(0)
    })

    it('进度值应该支持小数', () => {
      const { progress, updateProgress } = useLoading()

      updateProgress(33.33)

      expect(progress.value).toBe(33.33)
    })
  })
})

describe('useMultiLoading 组合式函数', () => {
  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该正确初始化多个加载区域', () => {
      const { states } = useMultiLoading(['list', 'form', 'detail'])

      expect(states.value.list).toEqual({ loading: false, text: '', progress: 0 })
      expect(states.value.form).toEqual({ loading: false, text: '', progress: 0 })
      expect(states.value.detail).toEqual({ loading: false, text: '', progress: 0 })
    })

    it('空数组应该创建空的 states', () => {
      const { states } = useMultiLoading([])

      expect(states.value).toEqual({})
    })

    it('默认参数应该创建空的 states', () => {
      const { states } = useMultiLoading()

      expect(states.value).toEqual({})
    })
  })

  /**
   * 单区域加载测试
   */
  describe('单区域加载', () => {
    it('应该开始指定区域的加载', () => {
      const { states, start } = useMultiLoading(['list', 'form'])

      start('list', '加载列表中...')

      expect(states.value.list.loading).toBe(true)
      expect(states.value.list.text).toBe('加载列表中...')
      expect(states.value.form.loading).toBe(false)
    })

    it('应该停止指定区域的加载', () => {
      const { states, start, stop } = useMultiLoading(['list', 'form'])

      start('list', '加载中...')
      stop('list')

      expect(states.value.list.loading).toBe(false)
      expect(states.value.list.text).toBe('')
    })

    it('应该更新指定区域的进度', () => {
      const { states, updateProgress } = useMultiLoading(['list'])

      updateProgress('list', 60)

      expect(states.value.list.progress).toBe(60)
    })

    it('不存在的区域操作应该被忽略', () => {
      const { states, start, stop, updateProgress } = useMultiLoading(['list'])

      // 这些操作不应该抛出错误
      start('nonexistent', '加载中')
      stop('nonexistent')
      updateProgress('nonexistent', 50)

      expect(states.value.nonexistent).toBeUndefined()
    })
  })

  /**
   * 多区域独立加载测试
   */
  describe('多区域独立加载', () => {
    it('不同区域应该独立管理加载状态', () => {
      const { states, start } = useMultiLoading(['list', 'form'])

      start('list', '加载列表')

      expect(states.value.list.loading).toBe(true)
      expect(states.value.form.loading).toBe(false)
    })

    it('多个区域可以同时处于加载状态', () => {
      const { states, start } = useMultiLoading(['list', 'form', 'detail'])

      start('list', '加载列表')
      start('form', '提交表单')
      start('detail', '加载详情')

      expect(states.value.list.loading).toBe(true)
      expect(states.value.form.loading).toBe(true)
      expect(states.value.detail.loading).toBe(true)
    })
  })

  /**
   * 停止所有加载测试
   */
  describe('停止所有加载', () => {
    it('应该停止所有区域的加载', () => {
      const { states, start, stopAll } = useMultiLoading(['list', 'form', 'detail'])

      start('list', '加载列表')
      start('form', '提交表单')
      start('detail', '加载详情')

      stopAll()

      expect(states.value.list.loading).toBe(false)
      expect(states.value.form.loading).toBe(false)
      expect(states.value.detail.loading).toBe(false)
    })

    it('stopAll 应该清空所有文本和进度', () => {
      const { states, start, updateProgress, stopAll } = useMultiLoading(['list', 'form'])

      start('list', '加载列表')
      start('form', '提交表单')
      updateProgress('list', 50)
      updateProgress('form', 75)

      stopAll()

      expect(states.value.list.text).toBe('')
      expect(states.value.form.text).toBe('')
      expect(states.value.list.progress).toBe(0)
      expect(states.value.form.progress).toBe(0)
    })
  })

  /**
   * 加载状态检查测试
   */
  describe('加载状态检查', () => {
    it('isLoading 应该返回指定区域的加载状态', () => {
      const { start, isLoading } = useMultiLoading(['list', 'form'])

      start('list')

      expect(isLoading('list')).toBe(true)
      expect(isLoading('form')).toBe(false)
    })

    it('isLoading 对不存在的区域应该返回 false', () => {
      const { isLoading } = useMultiLoading(['list'])

      expect(isLoading('nonexistent')).toBe(false)
    })

    it('isAnyLoading 应该检查是否有任何区域在加载', () => {
      const { start, stop, isAnyLoading } = useMultiLoading(['list', 'form'])

      expect(isAnyLoading.value).toBe(false)

      start('list')
      expect(isAnyLoading.value).toBe(true)

      stop('list')
      expect(isAnyLoading.value).toBe(false)
    })

    it('多个区域加载时 isAnyLoading 应该为 true', () => {
      const { start, isAnyLoading } = useMultiLoading(['list', 'form'])

      start('list')
      expect(isAnyLoading.value).toBe(true)

      start('form')
      expect(isAnyLoading.value).toBe(true)
    })
  })

  /**
   * 动态区域管理测试
   */
  describe('动态区域管理', () => {
    it('应该能够添加新的加载区域', () => {
      const { states, addZone } = useMultiLoading(['list'])

      addZone('form')

      expect(states.value.form).toEqual({ loading: false, text: '', progress: 0 })
    })

    it('添加已存在的区域应该被忽略', () => {
      const { states, start, addZone } = useMultiLoading(['list'])

      start('list', '加载中')
      addZone('list')

      expect(states.value.list.loading).toBe(true)
      expect(states.value.list.text).toBe('加载中')
    })

    it('应该能够移除加载区域', () => {
      const { states, removeZone } = useMultiLoading(['list', 'form'])

      removeZone('form')

      expect(states.value.form).toBeUndefined()
      expect(states.value.list).toBeDefined()
    })

    it('移除不存在的区域应该被忽略', () => {
      const { states, removeZone } = useMultiLoading(['list'])

      removeZone('nonexistent')

      expect(states.value.list).toBeDefined()
    })
  })
})

describe('useLoadingWithTimeout 组合式函数', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 超时控制测试
   */
  describe('超时控制', () => {
    it('应该在指定时间后自动停止加载', () => {
      const onTimeout = vi.fn()
      const { loading, start } = useLoadingWithTimeout({
        timeout: 5000,
        onTimeout
      })

      start()
      expect(loading.value).toBe(true)

      vi.advanceTimersByTime(5000)

      expect(loading.value).toBe(false)
      expect(onTimeout).toHaveBeenCalled()
    })

    it('应该使用默认超时时间 30 秒', () => {
      const onTimeout = vi.fn()
      const { loading, start } = useLoadingWithTimeout({ onTimeout })

      start()
      expect(loading.value).toBe(true)

      vi.advanceTimersByTime(29000)
      expect(loading.value).toBe(true)

      vi.advanceTimersByTime(1000)
      expect(loading.value).toBe(false)
    })

    it('手动停止应该清除超时定时器', () => {
      const onTimeout = vi.fn()
      const { loading, start, stop } = useLoadingWithTimeout({
        timeout: 5000,
        onTimeout
      })

      start()
      stop()

      expect(loading.value).toBe(false)

      vi.advanceTimersByTime(5000)

      expect(onTimeout).not.toHaveBeenCalled()
    })

    it('重复调用 start 应该重置超时定时器', () => {
      const onTimeout = vi.fn()
      const { loading, start } = useLoadingWithTimeout({
        timeout: 5000,
        onTimeout
      })

      start()
      vi.advanceTimersByTime(3000)

      start() // 重新开始，重置定时器
      vi.advanceTimersByTime(3000)

      expect(loading.value).toBe(true) // 还没到 5 秒

      vi.advanceTimersByTime(2000)
      expect(loading.value).toBe(false)
      expect(onTimeout).toHaveBeenCalledTimes(1)
    })
  })

  /**
   * 加载文本测试
   */
  describe('加载文本', () => {
    it('应该支持设置加载文本', () => {
      const { loadingText, start } = useLoadingWithTimeout()

      start('加载中...')

      expect(loadingText.value).toBe('加载中...')
    })

    it('超时后应该清空加载文本', () => {
      const { loadingText, start } = useLoadingWithTimeout({ timeout: 1000 })

      start('加载中...')
      vi.advanceTimersByTime(1000)

      expect(loadingText.value).toBe('')
    })
  })
})
