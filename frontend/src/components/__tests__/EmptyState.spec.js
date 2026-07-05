/**
 * EmptyState 组件单元测试
 * 测试空状态组件的渲染、事件和样式变体
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import EmptyState from '../common/EmptyState.vue'

// 创建模拟组件
const MockElIcon = {
  name: 'ElIcon',
  props: ['size', 'color'],
  setup(props, { slots }) {
    return () => h('span', {
      class: 'el-icon',
      style: { fontSize: props.size + 'px', color: props.color }
    }, slots.default?.())
  }
}

const MockElButton = {
  name: 'ElButton',
  props: ['type', 'size'],
  emits: ['click'],
  setup(props, { slots, emit }) {
    return () => h('button', {
      class: ['el-button', props.type, props.size],
      onClick: () => emit('click')
    }, slots.default?.())
  }
}

// 模拟图标组件
const MockFolderOpened = { name: 'FolderOpened', render: () => h('span', { class: 'icon-folder' }) }
const MockSearch = { name: 'Search', render: () => h('span', { class: 'icon-search' }) }
const MockWarningFilled = { name: 'WarningFilled', render: () => h('span', { class: 'icon-warning' }) }
const MockDocument = { name: 'Document', render: () => h('span', { class: 'icon-document' }) }

describe('EmptyState 组件', () => {
  const globalComponents = {
    'el-icon': MockElIcon,
    'el-button': MockElButton,
    'FolderOpened': MockFolderOpened,
    'Search': MockSearch,
    'WarningFilled': MockWarningFilled,
    'Document': MockDocument
  }

  /**
   * 图标、标题、描述渲染测试
   */
  describe('图标、标题、描述渲染', () => {
    it('应该正确渲染标题', () => {
      const wrapper = mount(EmptyState, {
        props: { title: '暂无数据' },
        global: { components: globalComponents }
      })

      const title = wrapper.find('.empty-state__title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toBe('暂无数据')
    })

    it('应该正确渲染描述', () => {
      const wrapper = mount(EmptyState, {
        props: { description: '当前列表为空，请添加数据' },
        global: { components: globalComponents }
      })

      const description = wrapper.find('.empty-state__description')
      expect(description.exists()).toBe(true)
      expect(description.text()).toBe('当前列表为空，请添加数据')
    })

    it('应该同时渲染标题和描述', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '搜索结果为空',
          description: '没有找到匹配的内容，请尝试其他关键词'
        },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__title').text()).toBe('搜索结果为空')
      expect(wrapper.find('.empty-state__description').text()).toBe('没有找到匹配的内容，请尝试其他关键词')
    })

    it('没有标题时不应显示标题元素', () => {
      const wrapper = mount(EmptyState, {
        props: { description: '只有描述' },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__title').exists()).toBe(false)
    })

    it('没有描述时不应显示描述元素', () => {
      const wrapper = mount(EmptyState, {
        props: { title: '只有标题' },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__description').exists()).toBe(false)
    })
  })

  /**
   * 操作按钮渲染测试
   */
  describe('操作按钮渲染', () => {
    it('应该渲染操作按钮', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: '立即创建'
        },
        global: { components: globalComponents }
      })

      const action = wrapper.find('.empty-state__action')
      expect(action.exists()).toBe(true)
    })

    it('应该使用正确的按钮类型', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: '创建',
          actionType: 'primary'
        },
        global: { components: globalComponents }
      })

      const button = wrapper.find('.el-button')
      expect(button.classes()).toContain('primary')
    })

    it('应该使用正确的按钮尺寸', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: '创建',
          actionSize: 'large'
        },
        global: { components: globalComponents }
      })

      const button = wrapper.find('.el-button')
      expect(button.classes()).toContain('large')
    })

    it('没有 actionText 时不应显示操作按钮', () => {
      const wrapper = mount(EmptyState, {
        props: { title: '空状态' },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__action').exists()).toBe(false)
    })

    it('actionText 为空字符串时不应显示操作按钮', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: ''
        },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__action').exists()).toBe(false)
    })
  })

  /**
   * 操作按钮事件测试
   */
  describe('操作按钮事件', () => {
    it('点击操作按钮应触发 action 事件', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: '创建'
        },
        global: { components: globalComponents }
      })

      await wrapper.find('.el-button').trigger('click')
      expect(wrapper.emitted('action')).toBeTruthy()
      expect(wrapper.emitted('action')).toHaveLength(1)
    })

    it('多次点击应触发多次事件', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '空状态',
          actionText: '创建'
        },
        global: { components: globalComponents }
      })

      const button = wrapper.find('.el-button')
      await button.trigger('click')
      await button.trigger('click')
      await button.trigger('click')

      expect(wrapper.emitted('action')).toHaveLength(3)
    })
  })

  /**
   * 尺寸和颜色测试
   */
  describe('尺寸和颜色', () => {
    it('应该使用自定义图标尺寸', () => {
      const wrapper = mount(EmptyState, {
        props: { icon: 'FolderOpened', iconSize: 96 },
        global: { components: globalComponents }
      })

      const icon = wrapper.find('.el-icon')
      expect(icon.attributes('style')).toContain('96px')
    })

    it('应该使用自定义图标颜色', () => {
      const wrapper = mount(EmptyState, {
        props: { icon: 'FolderOpened', iconColor: '#ff0000' },
        global: { components: globalComponents }
      })

      const icon = wrapper.find('.el-icon')
      expect(icon.element.style.color).toBe('rgb(255, 0, 0)')
    })

    it('紧凑模式应该应用 compact 类', () => {
      const wrapper = mount(EmptyState, {
        props: { compact: true },
        global: { components: globalComponents }
      })

      expect(wrapper.classes()).toContain('empty-state--compact')
    })

    it('非紧凑模式不应该应用 compact 类', () => {
      const wrapper = mount(EmptyState, {
        props: { compact: false },
        global: { components: globalComponents }
      })

      expect(wrapper.classes()).not.toContain('empty-state--compact')
    })
  })

  /**
   * 插槽测试
   */
  describe('插槽', () => {
    it('应该渲染 action 插槽内容', () => {
      const wrapper = mount(EmptyState, {
        props: { title: '空状态' },
        slots: {
          action: '<button class="custom-action">自定义操作</button>'
        },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.custom-action').exists()).toBe(true)
      expect(wrapper.find('.custom-action').text()).toBe('自定义操作')
    })
  })

  /**
   * 综合场景测试
   */
  describe('综合场景', () => {
    it('应该正确渲染完整的空状态', () => {
      const wrapper = mount(EmptyState, {
        props: {
          icon: 'FolderOpened',
          title: '暂无项目',
          description: '您还没有创建任何项目，点击下方按钮开始创建',
          actionText: '创建项目',
          actionType: 'primary',
          actionSize: 'default'
        },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__icon').exists()).toBe(true)
      expect(wrapper.find('.empty-state__title').text()).toBe('暂无项目')
      expect(wrapper.find('.empty-state__description').text()).toBe('您还没有创建任何项目，点击下方按钮开始创建')
      expect(wrapper.find('.empty-state__action').exists()).toBe(true)
    })

    it('应该处理动态属性更新', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: '初始标题',
          description: '初始描述'
        },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__title').text()).toBe('初始标题')
      expect(wrapper.find('.empty-state__description').text()).toBe('初始描述')

      await wrapper.setProps({
        title: '更新后的标题',
        description: '更新后的描述'
      })

      expect(wrapper.find('.empty-state__title').text()).toBe('更新后的标题')
      expect(wrapper.find('.empty-state__description').text()).toBe('更新后的描述')
    })

    it('动态添加 actionText 时应该显示操作按钮', async () => {
      const wrapper = mount(EmptyState, {
        props: { title: '空状态' },
        global: { components: globalComponents }
      })

      expect(wrapper.find('.empty-state__action').exists()).toBe(false)

      await wrapper.setProps({ actionText: '立即操作' })

      expect(wrapper.find('.empty-state__action').exists()).toBe(true)
      expect(wrapper.find('.el-button').text()).toBe('立即操作')
    })
  })
})
