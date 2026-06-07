/**
 * PageHeader 组件单元测试
 * 测试页面头部组件的渲染、插槽和响应式布局
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import PageHeader from '../common/PageHeader.vue'

// 模拟 Breadcrumb 组件
vi.mock('../common/Breadcrumb.vue', () => ({
  default: {
    name: 'Breadcrumb',
    props: ['routes'],
    template: '<div class="breadcrumb-mock" :data-routes="JSON.stringify(routes)"><slot /></div>'
  }
}))

describe('PageHeader 组件', () => {
  /**
   * 标题和副标题渲染测试
   */
  describe('标题和副标题渲染', () => {
    it('应该正确渲染主标题', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      const title = wrapper.find('.header-title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toBe('页面标题')
    })

    it('应该正确渲染副标题', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          subtitle: '这是副标题描述'
        }
      })

      const subtitle = wrapper.find('.header-subtitle')
      expect(subtitle.exists()).toBe(true)
      expect(subtitle.text()).toBe('这是副标题描述')
    })

    it('没有副标题时不应显示副标题元素', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      expect(wrapper.find('.header-subtitle').exists()).toBe(false)
    })

    it('副标题为空字符串时不应显示副标题元素', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          subtitle: ''
        }
      })

      expect(wrapper.find('.header-subtitle').exists()).toBe(false)
    })
  })

  /**
   * 图标渲染测试
   */
  describe('图标渲染', () => {
    it('应该正确渲染传入的图标组件', () => {
      const MockIcon = {
        name: 'MockIcon',
        template: '<span class="mock-icon">Icon</span>'
      }

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          icon: MockIcon
        }
      })

      const iconContainer = wrapper.find('.header-icon')
      expect(iconContainer.exists()).toBe(true)
      expect(iconContainer.find('.mock-icon').exists()).toBe(true)
    })

    it('没有图标时不应显示图标容器', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      expect(wrapper.find('.header-icon').exists()).toBe(false)
    })

    it('图标为 null 时不应显示图标容器', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          icon: null
        }
      })

      expect(wrapper.find('.header-icon').exists()).toBe(false)
    })
  })

  /**
   * 面包屑渲染测试
   */
  describe('面包屑渲染', () => {
    it('默认应该显示面包屑', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      expect(wrapper.find('.breadcrumb-mock').exists()).toBe(true)
    })

    it('应该正确传递面包屑路由数据', () => {
      const breadcrumbs = [
        { path: '/', name: '首页' },
        { path: '/projects', name: '项目' },
        { path: '/projects/1', name: '当前项目' }
      ]

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          breadcrumbs
        }
      })

      const breadcrumb = wrapper.find('.breadcrumb-mock')
      expect(breadcrumb.exists()).toBe(true)
      expect(breadcrumb.attributes('data-routes')).toBe(JSON.stringify(breadcrumbs))
    })

    it('showBreadcrumb 为 false 时不应显示面包屑', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          showBreadcrumb: false
        }
      })

      expect(wrapper.find('.breadcrumb-mock').exists()).toBe(false)
    })

    it('空面包屑数组也应该渲染面包屑组件', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          breadcrumbs: []
        }
      })

      expect(wrapper.find('.breadcrumb-mock').exists()).toBe(true)
    })
  })

  /**
   * 操作按钮插槽测试
   */
  describe('操作按钮插槽', () => {
    it('应该渲染 actions 插槽内容', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        },
        slots: {
          actions: '<button class="custom-action">自定义按钮</button>'
        }
      })

      const actionsContainer = wrapper.find('.header-actions')
      expect(actionsContainer.exists()).toBe(true)
      expect(actionsContainer.find('.custom-action').exists()).toBe(true)
    })

    it('应该渲染 actions 属性配置的按钮', () => {
      const mockClick = vi.fn()
      const actions = [
        {
          component: 'button',
          text: '新建',
          props: { class: 'btn-primary' },
          onClick: mockClick
        }
      ]

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          actions
        }
      })

      const actionsContainer = wrapper.find('.header-actions')
      expect(actionsContainer.exists()).toBe(true)
      expect(actionsContainer.text()).toContain('新建')
    })

    it('没有操作时不应显示操作区域', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      expect(wrapper.find('.header-actions').exists()).toBe(false)
    })

    it('actions 为空数组时不应显示操作区域', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          actions: []
        }
      })

      expect(wrapper.find('.header-actions').exists()).toBe(false)
    })

    it('插槽优先级高于 actions 属性', () => {
      const actions = [
        {
          component: 'button',
          text: '属性按钮'
        }
      ]

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          actions
        },
        slots: {
          actions: '<button class="slot-button">插槽按钮</button>'
        }
      })

      const actionsContainer = wrapper.find('.header-actions')
      expect(actionsContainer.find('.slot-button').exists()).toBe(true)
      expect(actionsContainer.text()).toBe('插槽按钮')
    })
  })

  /**
   * 响应式布局测试
   */
  describe('响应式布局', () => {
    it('应该具有正确的容器结构', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      // 验证外层容器
      expect(wrapper.find('.page-header').exists()).toBe(true)
      // 验证内容容器
      expect(wrapper.find('.header-content').exists()).toBe(true)
      // 验证左侧区域
      expect(wrapper.find('.header-left').exists()).toBe(true)
    })

    it('左侧区域应包含图标和标题区域', () => {
      const MockIcon = {
        name: 'MockIcon',
        template: '<span>Icon</span>'
      }

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          subtitle: '副标题',
          icon: MockIcon
        }
      })

      const headerLeft = wrapper.find('.header-left')
      expect(headerLeft.find('.header-icon').exists()).toBe(true)
      expect(headerLeft.find('.header-titles').exists()).toBe(true)
      expect(headerLeft.find('.header-title').exists()).toBe(true)
      expect(headerLeft.find('.header-subtitle').exists()).toBe(true)
    })

    it('标题区域应正确包裹标题和副标题', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          subtitle: '副标题'
        }
      })

      const titlesContainer = wrapper.find('.header-titles')
      expect(titlesContainer.exists()).toBe(true)
      expect(titlesContainer.find('h1').exists()).toBe(true)
      expect(titlesContainer.find('p').exists()).toBe(true)
    })
  })

  /**
   * 样式类测试
   */
  describe('样式类', () => {
    it('应该具有正确的 CSS 类名', () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题'
        }
      })

      expect(wrapper.find('.page-header').exists()).toBe(true)
      expect(wrapper.find('.header-content').exists()).toBe(true)
      expect(wrapper.find('.header-left').exists()).toBe(true)
      expect(wrapper.find('.header-titles').exists()).toBe(true)
      expect(wrapper.find('.header-title').exists()).toBe(true)
    })

    it('图标容器应具有正确的样式类', () => {
      const MockIcon = {
        name: 'MockIcon',
        template: '<span>Icon</span>'
      }

      const wrapper = mount(PageHeader, {
        props: {
          title: '页面标题',
          icon: MockIcon
        }
      })

      const iconContainer = wrapper.find('.header-icon')
      expect(iconContainer.exists()).toBe(true)
    })
  })

  /**
   * 复杂场景测试
   */
  describe('复杂场景', () => {
    it('应该同时渲染所有元素', () => {
      const MockIcon = {
        name: 'MockIcon',
        template: '<span class="test-icon">Icon</span>'
      }

      const breadcrumbs = [
        { path: '/', name: '首页' },
        { path: '/list', name: '列表' }
      ]

      const wrapper = mount(PageHeader, {
        props: {
          title: '完整页面标题',
          subtitle: '详细描述信息',
          icon: MockIcon,
          breadcrumbs
        },
        slots: {
          actions: '<button class="action-btn">操作</button>'
        }
      })

      // 验证所有元素都存在
      expect(wrapper.find('.breadcrumb-mock').exists()).toBe(true)
      expect(wrapper.find('.header-icon').exists()).toBe(true)
      expect(wrapper.find('.header-title').text()).toBe('完整页面标题')
      expect(wrapper.find('.header-subtitle').text()).toBe('详细描述信息')
      expect(wrapper.find('.header-actions').exists()).toBe(true)
      expect(wrapper.find('.action-btn').exists()).toBe(true)
    })

    it('应该处理动态标题更新', async () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '初始标题'
        }
      })

      expect(wrapper.find('.header-title').text()).toBe('初始标题')

      await wrapper.setProps({ title: '更新后的标题' })

      expect(wrapper.find('.header-title').text()).toBe('更新后的标题')
    })

    it('应该处理动态副标题更新', async () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '标题',
          subtitle: '初始副标题'
        }
      })

      expect(wrapper.find('.header-subtitle').text()).toBe('初始副标题')

      await wrapper.setProps({ subtitle: '更新后的副标题' })

      expect(wrapper.find('.header-subtitle').text()).toBe('更新后的副标题')
    })

    it('动态添加副标题时应该显示副标题元素', async () => {
      const wrapper = mount(PageHeader, {
        props: {
          title: '标题'
        }
      })

      expect(wrapper.find('.header-subtitle').exists()).toBe(false)

      await wrapper.setProps({ subtitle: '新增的副标题' })

      expect(wrapper.find('.header-subtitle').exists()).toBe(true)
      expect(wrapper.find('.header-subtitle').text()).toBe('新增的副标题')
    })
  })
})
