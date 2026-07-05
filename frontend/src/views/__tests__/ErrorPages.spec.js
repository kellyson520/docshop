import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import NotFound from '../NotFound.vue'
import AccessDenied from '../AccessDenied.vue'

const DummyView = { template: '<div />' }

async function mountWithRouter(component, initialPath) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: DummyView },
      { path: '/login', component: DummyView },
      { path: '/admin/projects', component: DummyView },
      { path: '/access-denied', component: DummyView },
      { path: '/:pathMatch(.*)*', component: DummyView }
    ]
  })

  await router.push(initialPath)
  await router.isReady()

  const pushSpy = vi.spyOn(router, 'push')
  const replaceSpy = vi.spyOn(router, 'replace')
  const backSpy = vi.spyOn(router, 'back')

  const wrapper = mount(component, {
    global: {
      plugins: [router]
    }
  })

  return { wrapper, router, pushSpy, replaceSpy, backSpy }
}

describe('error page copy and actions', () => {
  it('NotFound renders readable Chinese copy and current path', async () => {
    const { wrapper } = await mountWithRouter(NotFound, '/missing/path?x=1')

    expect(wrapper.text()).toContain('这份文档走丢了')
    expect(wrapper.text()).toContain('当前路径')
    expect(wrapper.text()).toContain('/missing/path?x=1')
    expect(wrapper.text()).not.toContain('杩')
    expect(wrapper.text()).not.toContain('鍥')
  })

  it('AccessDenied explains missing credentials and keeps retry target', async () => {
    const { wrapper, pushSpy, replaceSpy } = await mountWithRouter(
      AccessDenied,
      '/access-denied?reason=missing_credentials&redirect=/admin/projects'
    )

    expect(wrapper.text()).toContain('当前访问未通过门禁')
    expect(wrapper.text()).toContain('未登录，且未携带访问 token')
    expect(wrapper.text()).toContain('/admin/projects')
    expect(wrapper.text()).not.toContain('褰')

    const buttons = wrapper.findAll('button')
    await buttons[0].trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ path: '/login', query: { redirect: '/admin/projects' } })

    await buttons[1].trigger('click')
    expect(replaceSpy).toHaveBeenCalledWith('/admin/projects')
  })
})
