/**
 * CardList 组件单元测试
 * 测试卡片列表组件的渲染、响应式布局和交互功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import CardList from '../card/CardGrid.vue'

// 模拟 Element Plus 组件
vi.mock('element-plus', () => ({
  ElEmpty: {
    name: 'ElEmpty',
    props: ['description'],
    template: '<div class="el-empty"><slot name="image"/>{{ description }}</div>'
  },
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template: '<span class="el-icon" :style="{ fontSize: size + \'px\', color }"><slot /></span>'
  }
}))

// 模拟 Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Folder: { name: 'Folder', template: '<span class="icon-folder" />' }
}))

// 模拟响应式组合式函数
const mockBreakpoint = ref('lg')
const mockIsXl = ref(false)
const mockIsLg = ref(true)
const mockIsMd = ref(false)
const mockIsSm = ref(false)
const mockIsXs = ref(false)

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    currentBreakpoint: mockBreakpoint,
    isXl: mockIsXl,
    isLg: mockIsLg,
    isMd: mockIsMd,
    isSm: mockIsSm,
    isXs: mockIsXs
  })
}))

// 模拟 FileCard 组件
vi.mock('../card/FileCard.vue', () => ({
  default: {
    name: 'FileCard',
    props: ['card'],
    template: '<div class="file-card-mock" @click="$emit(\'click\', card)">{{ card.display_name }}</div>'
  }
}))

// 模拟 SkeletonCard 组件
vi.mock('@/components/common/SkeletonCard.vue', () => ({
  default: {
    name: 'SkeletonCard',
    template: '<div class="skeleton-card-mock">Skeleton</div>'
  }
}))

describe('CardList 组件', () => {
  // 基础测试数据
  const mockCards = [
    {
      id: 1,
      display_name: '文档1',
      filename: 'doc1.pdf',
      file_type: 'pdf',
      version_count: 3,
      updated_at: new Date().toISOString(),
      tags: ['标签1']
    },
    {
      id: 2,
      display_name: '文档2',
      filename: 'doc2.docx',
      file_type: 'docx',
      version_count: 5,
      updated_at: new Date().toISOString(),
      tags: ['标签2', '标签3']
    },
    {
      id: 3,
      display_name: '文档3',
      filename: 'doc3.xlsx',
      file_type: 'xlsx',
      version_count: 2,
      updated_at: new Date().toISOString(),
      tags: []
    }
  ]

  beforeEach(() => {
    // 重置响应式状态
    mockBreakpoint.value = 'lg'
    mockIsXl.value = false
    mockIsLg.value = true
    mockIsMd.value = false
    mockIsSm.value = false
    mockIsXs.value = false
  })

  /**
   * 渲染测试
   */
  describe('渲染', () => {
    it('应该正确渲染卡片列表', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const cardElements = wrapper.findAll('.file-card-mock')
      expect(cardElements.length).toBe(3)
    })

    it('应该正确传递卡片数据给子组件', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const cardElements = wrapper.findAll('.file-card-mock')
      expect(cardElements[0].text()).toBe('文档1')
      expect(cardElements[1].text()).toBe('文档2')
      expect(cardElements[2].text()).toBe('文档3')
    })

    it('空列表时应该显示空状态', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: [],
          loading: false
        }
      })

      expect(wrapper.find('.el-empty').exists()).toBe(true)
      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })

    it('加载中时不应显示空状态', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: [],
          loading: true
        }
      })

      expect(wrapper.find('.el-empty').exists()).toBe(false)
      expect(wrapper.find('.empty-state').exists()).toBe(false)
    })

    it('有数据时不应显示空状态', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      expect(wrapper.find('.empty-state').exists()).toBe(false)
    })
  })

  /**
   * 加载状态测试
   */
  describe('加载状态', () => {
    it('加载中应该显示骨架屏', () => {
      mockIsLg.value = true
      mockIsMd.value = false

      const wrapper = mount(CardList, {
        props: {
          cards: [],
          loading: true
        }
      })

      const skeletons = wrapper.findAll('.skeleton-card-mock')
      // lg 屏幕下是 4 列，骨架屏数量 = 列数 * 2 = 8
      expect(skeletons.length).toBe(8)
    })

    it('非加载状态不应显示骨架屏', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const skeletons = wrapper.findAll('.skeleton-card-mock')
      expect(skeletons.length).toBe(0)
    })

    it('加载完成后应该显示卡片', async () => {
      const wrapper = mount(CardList, {
        props: {
          cards: [],
          loading: true
        }
      })

      expect(wrapper.findAll('.skeleton-card-mock').length).toBeGreaterThan(0)

      await wrapper.setProps({ cards: mockCards, loading: false })

      expect(wrapper.findAll('.skeleton-card-mock').length).toBe(0)
      expect(wrapper.findAll('.file-card-mock').length).toBe(3)
    })
  })

  /**
   * 响应式布局测试
   */
  describe('响应式布局', () => {
    it('xl 屏幕应该使用正确的列数', async () => {
      mockIsXl.value = true
      mockIsLg.value = false

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-4') // xl 默认 4 列
    })

    it('lg 屏幕应该使用正确的列数', async () => {
      mockIsLg.value = true

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-4') // lg 默认 4 列
    })

    it('md 屏幕应该使用正确的列数', async () => {
      mockIsLg.value = false
      mockIsMd.value = true

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-3') // md 默认 3 列
    })

    it('sm 屏幕应该使用正确的列数', async () => {
      mockIsLg.value = false
      mockIsMd.value = false
      mockIsSm.value = true

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-2') // sm 默认 2 列
    })

    it('xs 屏幕应该使用正确的列数', async () => {
      mockIsLg.value = false
      mockIsMd.value = false
      mockIsSm.value = false
      mockIsXs.value = true

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-1') // xs 默认 1 列
    })

    it('应该支持自定义列数配置', async () => {
      mockIsXl.value = true
      mockIsLg.value = false

      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: true,
          columns: {
            xl: 6,
            lg: 4,
            md: 3,
            sm: 2,
            xs: 1
          }
        }
      })

      await nextTick()

      const grid = wrapper.find('.card-grid')
      expect(grid.classes()).toContain('grid-cols-6') // 自定义 xl 为 6 列
    })
  })

  /**
   * 间距测试
   */
  describe('间距配置', () => {
    it('应该使用默认间距', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const gridItems = wrapper.findAll('.grid-item')
      expect(gridItems.length).toBeGreaterThan(0)
      // 默认间距为 20px
      expect(gridItems[0].attributes('style')).toContain('margin-bottom: 20px')
    })

    it('应该支持数字类型的间距', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false,
          gap: 30
        }
      })

      const gridItems = wrapper.findAll('.grid-item')
      expect(gridItems[0].attributes('style')).toContain('margin-bottom: 30px')
    })

    it('应该支持字符串类型的间距', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false,
          gap: '2rem'
        }
      })

      const gridItems = wrapper.findAll('.grid-item')
      expect(gridItems[0].attributes('style')).toContain('margin-bottom: 2rem')
    })
  })

  /**
   * 点击事件测试
   */
  describe('点击事件', () => {
    it('点击卡片应该触发 card-click 事件', async () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const firstCard = wrapper.find('.file-card-mock')
      await firstCard.trigger('click')

      expect(wrapper.emitted('card-click')).toBeTruthy()
      expect(wrapper.emitted('card-click')[0]).toEqual([mockCards[0]])
    })

    it('点击不同卡片应该传递不同的数据', async () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards,
          loading: false
        }
      })

      const cards = wrapper.findAll('.file-card-mock')

      await cards[0].trigger('click')
      expect(wrapper.emitted('card-click')[0]).toEqual([mockCards[0]])

      await cards[1].trigger('click')
      expect(wrapper.emitted('card-click')[1]).toEqual([mockCards[1]])

      await cards[2].trigger('click')
      expect(wrapper.emitted('card-click')[2]).toEqual([mockCards[2]])
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('cards 为 null 时不应报错', () => {
      expect(() => {
        mount(CardList, {
          props: {
            cards: null,
            loading: false
          }
        })
      }).not.toThrow()
    })

    it('cards 为 undefined 时不应报错', () => {
      expect(() => {
        mount(CardList, {
          props: {
            cards: undefined,
            loading: false
          }
        })
      }).not.toThrow()
    })

    it('单个卡片应该正确渲染', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: [mockCards[0]],
          loading: false
        }
      })

      const cardElements = wrapper.findAll('.file-card-mock')
      expect(cardElements.length).toBe(1)
    })

    it('大量卡片应该正确渲染', () => {
      const manyCards = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1,
        display_name: `文档${i + 1}`,
        filename: `doc${i + 1}.pdf`,
        file_type: 'pdf',
        version_count: 1,
        updated_at: new Date().toISOString(),
        tags: []
      }))

      const wrapper = mount(CardList, {
        props: {
          cards: manyCards,
          loading: false
        }
      })

      const cardElements = wrapper.findAll('.file-card-mock')
      expect(cardElements.length).toBe(100)
    })

    it('卡片数据变化时应该正确更新', async () => {
      const wrapper = mount(CardList, {
        props: {
          cards: mockCards.slice(0, 1),
          loading: false
        }
      })

      expect(wrapper.findAll('.file-card-mock').length).toBe(1)

      await wrapper.setProps({ cards: mockCards })

      expect(wrapper.findAll('.file-card-mock').length).toBe(3)
    })
  })

  /**
   * Props 验证测试
   */
  describe('Props 验证', () => {
    it('应该接受默认的 props', () => {
      const wrapper = mount(CardList)

      expect(wrapper.find('.card-grid').exists()).toBe(true)
      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })

    it('loading 默认为 false', () => {
      const wrapper = mount(CardList, {
        props: {
          cards: []
        }
      })

      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })

    it('cards 默认为空数组', () => {
      const wrapper = mount(CardList)

      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })
  })
})
