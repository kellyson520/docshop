import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ShareLayout from '../ShareLayout.vue'

const routeState = {
  path: '/s/share-token',
  params: { token: 'share-token' },
}

const shareSessionMock = vi.hoisted(() => ({
  tabId: 'share-tab-1',
  grantToken: { value: '' },
  heartbeat: vi.fn(() => Promise.resolve({ active: true })),
  release: vi.fn(() => Promise.resolve({ released: true })),
  releaseOnPageHide: vi.fn(() => true),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRoute: () => routeState,
    onBeforeRouteLeave: vi.fn(),
  }
})

vi.mock('@/composables/useShareSession', () => ({
  useShareSession: () => shareSessionMock,
}))

describe('ShareLayout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    routeState.path = '/s/share-token'
    routeState.params = { token: 'share-token' }
    shareSessionMock.grantToken.value = ''
    shareSessionMock.heartbeat.mockClear()
    shareSessionMock.release.mockClear()
    shareSessionMock.releaseOnPageHide.mockClear()
  })

  it('renders a dedicated header toolbar that keeps the back action and theme toggle together', () => {
    const wrapper = mount(ShareLayout, {
      global: {
        stubs: {
          RouterLink: { template: '<a class="router-link"><slot /></a>' },
          RouterView: { template: '<div class="router-view-stub" />' }
        }
      }
    })

    const toolbar = wrapper.find('[data-testid="share-header-toolbar"]')

    expect(toolbar.exists()).toBe(true)
    expect(toolbar.find('.back-button').exists()).toBe(true)
    expect(toolbar.find('.theme-toggle').exists()).toBe(true)

    wrapper.unmount()
  })

  it('removes shared chrome and width constraints on preview routes', () => {
    routeState.path = '/s/share-token/preview/file-1'

    const wrapper = mount(ShareLayout, {
      global: {
        stubs: {
          RouterLink: { template: '<a class="router-link"><slot /></a>' },
          RouterView: { template: '<div class="router-view-stub" />' }
        }
      }
    })

    expect(wrapper.find('.share-header').exists()).toBe(false)
    expect(wrapper.find('.share-footer').exists()).toBe(false)
    expect(wrapper.find('.share-main').classes()).toContain('share-main--preview')

    wrapper.unmount()
  })

  it('releases password grants when the share tab is hidden or closed', async () => {
    shareSessionMock.grantToken.value = 'grant-1'

    const wrapper = mount(ShareLayout, {
      global: {
        stubs: {
          RouterLink: { template: '<a class="router-link"><slot /></a>' },
          RouterView: { template: '<div class="router-view-stub" />' }
        }
      }
    })

    window.dispatchEvent(new Event('pagehide'))

    expect(shareSessionMock.releaseOnPageHide).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })
})
