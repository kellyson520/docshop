import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ScrollNotice from '../common/ScrollNotice.vue'

const notices = [
  { message: '系统维护通知', tag: '公告', tagType: 'warning' }
]

function setContainerSize(wrapper, { offsetWidth, scrollWidth }) {
  const container = wrapper.find('.scroll-container').element
  Object.defineProperty(container, 'offsetWidth', {
    configurable: true,
    value: offsetWidth
  })
  Object.defineProperty(container, 'scrollWidth', {
    configurable: true,
    value: scrollWidth
  })
}

describe('ScrollNotice', () => {
  let requestAnimationFrameMock
  let cancelAnimationFrameMock

  beforeEach(() => {
    vi.useFakeTimers()
    requestAnimationFrameMock = vi.fn(() => 101)
    cancelAnimationFrameMock = vi.fn()
    vi.stubGlobal('requestAnimationFrame', requestAnimationFrameMock)
    vi.stubGlobal('cancelAnimationFrame', cancelAnimationFrameMock)
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('短公告内容小于容器宽度时仍会进入滚动循环', async () => {
    const wrapper = mount(ScrollNotice, {
      props: {
        notices,
        speed: 60
      }
    })

    setContainerSize(wrapper, { offsetWidth: 500, scrollWidth: 200 })
    await vi.advanceTimersByTimeAsync(100)
    await nextTick()

    expect(requestAnimationFrameMock).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.scroll-content').attributes('style')).toContain('translateX(-1px)')
  })

  it('卸载组件时会取消尚未触发的延迟滚动任务', () => {
    const wrapper = mount(ScrollNotice, {
      props: {
        notices,
        speed: 60
      }
    })

    expect(vi.getTimerCount()).toBeGreaterThan(0)

    wrapper.unmount()

    expect(vi.getTimerCount()).toBe(0)
    vi.advanceTimersByTime(100)
    expect(requestAnimationFrameMock).not.toHaveBeenCalled()
  })
})
