import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import {
  createAnchorLink,
  getDocumentScrollElement,
  getElementDocumentScrollTop,
  getWindowScrollPosition,
  scrollDocumentTo,
  useScroll,
} from '../useScroll'

describe('useScroll document root helpers', () => {
  it('prefers body as the active scroll root when body carries the vertical scroll state', () => {
    const body = {
      scrollTop: 480,
      scrollLeft: 12,
      scrollHeight: 2400,
      clientHeight: 900,
    }
    const documentElement = {
      scrollTop: 0,
      scrollLeft: 0,
      scrollHeight: 900,
      clientHeight: 900,
    }
    const doc = {
      body,
      documentElement,
      scrollingElement: documentElement,
    }

    expect(getDocumentScrollElement(doc)).toBe(body)
    expect(getWindowScrollPosition({ pageXOffset: 0, pageYOffset: 0 }, doc)).toEqual({
      x: 12,
      y: 480,
    })
  })

  it('scrolls the resolved document root instead of only relying on window.scrollTo', () => {
    const body = {
      scrollTop: 860,
      scrollLeft: 0,
      scrollHeight: 3200,
      clientHeight: 900,
      scrollTo: vi.fn(({ left, top }) => {
        body.scrollLeft = left
        body.scrollTop = top
      }),
    }
    const documentElement = {
      scrollTop: 0,
      scrollLeft: 0,
      scrollHeight: 900,
      clientHeight: 900,
    }
    const doc = {
      body,
      documentElement,
      scrollingElement: documentElement,
    }
    const win = {
      pageXOffset: 0,
      pageYOffset: 0,
      scrollTo: vi.fn(),
    }

    scrollDocumentTo(win, doc, 0, 0, 'smooth')

    expect(body.scrollTo).toHaveBeenCalledWith({
      left: 0,
      top: 0,
      behavior: 'smooth',
    })
    expect(body.scrollTop).toBe(0)
  })

  it('computes target element scroll top from the active scroll root instead of window.pageYOffset', () => {
    const body = {
      scrollTop: 520,
      scrollLeft: 0,
      scrollHeight: 3200,
      clientHeight: 900,
    }
    const documentElement = {
      scrollTop: 0,
      scrollLeft: 0,
      scrollHeight: 900,
      clientHeight: 900,
    }
    const doc = {
      body,
      documentElement,
      scrollingElement: documentElement,
    }
    const win = {
      pageXOffset: 0,
      pageYOffset: 0,
    }
    const target = {
      getBoundingClientRect: () => ({ top: 240 }),
    }

    expect(getElementDocumentScrollTop(target, win, doc, -64)).toBe(696)
  })

  it('scrollToElement scrolls the active body root for document anchors', () => {
    const originalQuerySelector = document.querySelector.bind(document)
    const originalBodyScrollTop = document.body.scrollTop
    const originalBodyScrollLeft = document.body.scrollLeft
    const originalBodyScrollHeight = document.body.scrollHeight
    const originalBodyClientHeight = document.body.clientHeight
    const originalDocumentElementScrollTop = document.documentElement.scrollTop
    const originalDocumentElementScrollLeft = document.documentElement.scrollLeft
    const originalDocumentElementScrollHeight = document.documentElement.scrollHeight
    const originalDocumentElementClientHeight = document.documentElement.clientHeight
    const originalScrollingElement = document.scrollingElement
    const originalWindowScrollTo = window.scrollTo
    const bodyScrollTo = vi.fn(({ left, top }) => {
      document.body.scrollLeft = left
      document.body.scrollTop = top
    })
    const target = {
      getBoundingClientRect: () => ({ top: 180 }),
    }

    document.body.scrollTop = 500
    document.body.scrollLeft = 0
    Object.defineProperty(document.body, 'scrollHeight', { configurable: true, value: 3200 })
    Object.defineProperty(document.body, 'clientHeight', { configurable: true, value: 900 })
    document.body.scrollTo = bodyScrollTo
    document.documentElement.scrollTop = 0
    document.documentElement.scrollLeft = 0
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: 900 })
    Object.defineProperty(document.documentElement, 'clientHeight', { configurable: true, value: 900 })
    Object.defineProperty(document, 'scrollingElement', { configurable: true, value: document.documentElement })
    document.querySelector = vi.fn((selector) => (selector === '#target' ? target : originalQuerySelector(selector)))
    window.scrollTo = vi.fn()

    let api
    const Probe = defineComponent({
      setup() {
        api = useScroll()
        return () => h('div')
      },
    })

    mount(Probe)
    api.scrollToElement('#target', { offset: -64, behavior: 'smooth' })

    expect(bodyScrollTo).toHaveBeenCalledWith({
      left: 0,
      top: 616,
      behavior: 'smooth',
    })
    expect(document.body.scrollTop).toBe(616)

    document.querySelector = originalQuerySelector
    document.body.scrollTop = originalBodyScrollTop
    document.body.scrollLeft = originalBodyScrollLeft
    Object.defineProperty(document.body, 'scrollHeight', { configurable: true, value: originalBodyScrollHeight })
    Object.defineProperty(document.body, 'clientHeight', { configurable: true, value: originalBodyClientHeight })
    document.documentElement.scrollTop = originalDocumentElementScrollTop
    document.documentElement.scrollLeft = originalDocumentElementScrollLeft
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: originalDocumentElementScrollHeight })
    Object.defineProperty(document.documentElement, 'clientHeight', { configurable: true, value: originalDocumentElementClientHeight })
    Object.defineProperty(document, 'scrollingElement', { configurable: true, value: originalScrollingElement })
    window.scrollTo = originalWindowScrollTo
  })

  it('createAnchorLink scrolls the active body root for hash targets', () => {
    const originalQuerySelector = document.querySelector.bind(document)
    const originalBodyScrollTop = document.body.scrollTop
    const originalBodyScrollLeft = document.body.scrollLeft
    const originalBodyScrollHeight = document.body.scrollHeight
    const originalBodyClientHeight = document.body.clientHeight
    const originalDocumentElementScrollTop = document.documentElement.scrollTop
    const originalDocumentElementScrollLeft = document.documentElement.scrollLeft
    const originalDocumentElementScrollHeight = document.documentElement.scrollHeight
    const originalDocumentElementClientHeight = document.documentElement.clientHeight
    const originalScrollingElement = document.scrollingElement
    const originalWindowScrollTo = window.scrollTo
    const bodyScrollTo = vi.fn(({ left, top }) => {
      document.body.scrollLeft = left
      document.body.scrollTop = top
    })
    const target = {
      getBoundingClientRect: () => ({ top: 140 }),
    }

    document.body.scrollTop = 300
    document.body.scrollLeft = 0
    Object.defineProperty(document.body, 'scrollHeight', { configurable: true, value: 3200 })
    Object.defineProperty(document.body, 'clientHeight', { configurable: true, value: 900 })
    document.body.scrollTo = bodyScrollTo
    document.documentElement.scrollTop = 0
    document.documentElement.scrollLeft = 0
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: 900 })
    Object.defineProperty(document.documentElement, 'clientHeight', { configurable: true, value: 900 })
    Object.defineProperty(document, 'scrollingElement', { configurable: true, value: document.documentElement })
    document.querySelector = vi.fn((selector) => (selector === '#anchor' ? target : originalQuerySelector(selector)))
    window.scrollTo = vi.fn()

    const preventDefault = vi.fn()
    const handler = createAnchorLink('#anchor', { offset: -64, behavior: 'smooth' })
    handler({ preventDefault })

    expect(preventDefault).toHaveBeenCalled()
    expect(bodyScrollTo).toHaveBeenCalledWith({
      left: 0,
      top: 376,
      behavior: 'smooth',
    })
    expect(document.body.scrollTop).toBe(376)

    document.querySelector = originalQuerySelector
    document.body.scrollTop = originalBodyScrollTop
    document.body.scrollLeft = originalBodyScrollLeft
    Object.defineProperty(document.body, 'scrollHeight', { configurable: true, value: originalBodyScrollHeight })
    Object.defineProperty(document.body, 'clientHeight', { configurable: true, value: originalBodyClientHeight })
    document.documentElement.scrollTop = originalDocumentElementScrollTop
    document.documentElement.scrollLeft = originalDocumentElementScrollLeft
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: originalDocumentElementScrollHeight })
    Object.defineProperty(document.documentElement, 'clientHeight', { configurable: true, value: originalDocumentElementClientHeight })
    Object.defineProperty(document, 'scrollingElement', { configurable: true, value: originalScrollingElement })
    window.scrollTo = originalWindowScrollTo
  })
})
