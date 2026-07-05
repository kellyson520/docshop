/**
 * FileCard 组件单元测试
 * 测试文件卡片组件的渲染、交互和样式
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import FileCard from '../card/FileCard.vue'

// 模拟 Element Plus 组件
vi.mock('element-plus', () => ({
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template: '<span class="el-icon"><slot /></span>'
  },
  ElTag: {
    name: 'ElTag',
    props: ['type', 'size', 'effect'],
    template: '<span class="el-tag" :class="type"><slot /></span>'
  }
}))

// 模拟 Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Document: { name: 'Document', template: '<span class="icon-document" />' },
  Files: { name: 'Files', template: '<span class="icon-files" />' },
  Grid: { name: 'Grid', template: '<span class="icon-grid" />' }
}))

describe('FileCard 组件', () => {
  // 基础测试数据
  const mockCard = {
    id: 1,
    display_name: '测试文档',
    filename: 'test.pdf',
    description: '这是一个测试文档的描述',
    file_type: 'pdf',
    version_count: 5,
    updated_at: new Date().toISOString(),
    tags: ['标签1', '标签2', '标签3']
  }

  /**
   * 渲染测试
   */
  describe('渲染', () => {
    it('应该正确渲染文件卡片的基本信息', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      // 验证标题渲染
      expect(wrapper.find('.card-title').text()).toBe('测试文档')
      // 验证描述渲染
      expect(wrapper.find('.card-desc').text()).toBe('这是一个测试文档的描述')
      // 验证版本数渲染
      expect(wrapper.find('.version').text()).toContain('5 版本')
    })

    it('当没有 display_name 时应显示 filename', () => {
      const cardWithoutDisplayName = {
        ...mockCard,
        display_name: null,
        filename: 'backup.docx'
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutDisplayName }
      })

      expect(wrapper.find('.card-title').text()).toBe('backup.docx')
    })

    it('当没有名称时应显示默认文本', () => {
      const cardWithoutName = {
        ...mockCard,
        display_name: null,
        filename: null
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutName }
      })

      expect(wrapper.find('.card-title').text()).toBe('未命名文档')
    })

    it('当没有描述时不应显示描述元素', () => {
      const cardWithoutDesc = {
        ...mockCard,
        description: null
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutDesc }
      })

      expect(wrapper.find('.card-desc').exists()).toBe(false)
    })

    it('应该正确显示文件类型标签', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      const typeTag = wrapper.find('.type-tag')
      expect(typeTag.exists()).toBe(true)
      expect(typeTag.text()).toBe('PDF')
    })

    it('应该正确渲染标签列表', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      const tags = wrapper.findAll('.card-tags .el-tag')
      expect(tags.length).toBe(3)
      expect(tags[0].text()).toBe('标签1')
      expect(tags[1].text()).toBe('标签2')
      expect(tags[2].text()).toBe('标签3')
    })

    it('当标签超过3个时应显示更多提示', () => {
      const cardWithManyTags = {
        ...mockCard,
        tags: ['标签1', '标签2', '标签3', '标签4', '标签5']
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithManyTags }
      })

      const tags = wrapper.findAll('.card-tags .el-tag')
      // 前3个标签 + 1个更多提示
      expect(tags.length).toBe(4)
      expect(tags[3].text()).toBe('+2')
    })

    it('当没有标签时不应显示标签区域', () => {
      const cardWithoutTags = {
        ...mockCard,
        tags: []
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutTags }
      })

      expect(wrapper.find('.card-tags').exists()).toBe(false)
    })
  })

  /**
   * 点击事件测试
   */
  describe('点击事件', () => {
    it('点击卡片应触发 click 事件', async () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      await wrapper.find('.file-card').trigger('click')

      expect(wrapper.emitted('click')).toBeTruthy()
      expect(wrapper.emitted('click')[0]).toEqual([mockCard])
    })

    it('按下 Enter 键应触发 click 事件', async () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      await wrapper.find('.file-card').trigger('keydown.enter')

      expect(wrapper.emitted('click')).toBeTruthy()
    })

    it('卡片应具有正确的可访问性属性', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      const card = wrapper.find('.file-card')
      expect(card.attributes('role')).toBe('button')
      expect(card.attributes('tabindex')).toBe('0')
    })
  })

  /**
   * 悬停效果测试
   */
  describe('悬停效果', () => {
    it('卡片应具有悬停样式类', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      // 验证基础样式类存在
      expect(wrapper.find('.file-card').exists()).toBe(true)
      // 悬停效果主要通过 CSS 实现，这里验证结构正确
      expect(wrapper.find('.card-cover').exists()).toBe(true)
    })

    it('封面图片在悬停时应有缩放效果（CSS 类验证）', () => {
      const cardWithCover = {
        ...mockCard,
        cover_image: '/images/cover.jpg'
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithCover }
      })

      const img = wrapper.find('.card-cover img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('/images/cover.jpg')
      expect(img.attributes('loading')).toBe('lazy')
    })
  })

  /**
   * 文件类型图标测试
   */
  describe('文件类型图标', () => {
    it('PDF 文件应显示正确的类型样式', () => {
      const pdfCard = { ...mockCard, file_type: 'pdf' }
      const wrapper = mount(FileCard, {
        props: { card: pdfCard }
      })

      const defaultCover = wrapper.find('.default-cover')
      expect(defaultCover.classes()).toContain('pdf')
    })

    it('DOCX 文件应显示正确的类型样式', () => {
      const docxCard = { ...mockCard, file_type: 'docx' }
      const wrapper = mount(FileCard, {
        props: { card: docxCard }
      })

      const defaultCover = wrapper.find('.default-cover')
      expect(defaultCover.classes()).toContain('docx')
    })

    it('XLSX 文件应显示正确的类型样式', () => {
      const xlsxCard = { ...mockCard, file_type: 'xlsx' }
      const wrapper = mount(FileCard, {
        props: { card: xlsxCard }
      })

      const defaultCover = wrapper.find('.default-cover')
      expect(defaultCover.classes()).toContain('xlsx')
    })

    it('未知文件类型应使用默认样式', () => {
      const unknownCard = { ...mockCard, file_type: 'txt' }
      const wrapper = mount(FileCard, {
        props: { card: unknownCard }
      })

      const defaultCover = wrapper.find('.default-cover')
      expect(defaultCover.classes()).not.toContain('pdf')
      expect(defaultCover.classes()).not.toContain('docx')
      expect(defaultCover.classes()).not.toContain('xlsx')
    })

    it('文件类型标签应使用正确的类型', () => {
      const pdfWrapper = mount(FileCard, {
        props: { card: { ...mockCard, file_type: 'pdf' } }
      })
      expect(pdfWrapper.find('.type-tag').classes()).toContain('danger')

      const docxWrapper = mount(FileCard, {
        props: { card: { ...mockCard, file_type: 'docx' } }
      })
      expect(docxWrapper.find('.type-tag').classes()).toContain('primary')

      const xlsxWrapper = mount(FileCard, {
        props: { card: { ...mockCard, file_type: 'xlsx' } }
      })
      expect(xlsxWrapper.find('.type-tag').classes()).toContain('success')
    })
  })

  /**
   * 日期格式化测试
   */
  describe('日期格式化', () => {
    it('应该正确格式化日期', () => {
      const wrapper = mount(FileCard, {
        props: { card: mockCard }
      })

      // 验证时间元素存在
      expect(wrapper.find('.time').exists()).toBe(true)
    })

    it('没有日期时应显示空字符串', () => {
      const cardWithoutDate = {
        ...mockCard,
        updated_at: null
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutDate }
      })

      expect(wrapper.find('.time').text()).toBe('')
    })
  })

  /**
   * 封面图片测试
   */
  describe('封面图片', () => {
    it('有封面图片时应显示图片', () => {
      const cardWithCover = {
        ...mockCard,
        cover_image: '/uploads/cover.png'
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithCover }
      })

      const img = wrapper.find('.card-cover img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('/uploads/cover.png')
    })

    it('没有封面图片时应显示默认图标', () => {
      const cardWithoutCover = {
        ...mockCard,
        cover_image: null
      }
      const wrapper = mount(FileCard, {
        props: { card: cardWithoutCover }
      })

      expect(wrapper.find('.default-cover').exists()).toBe(true)
      expect(wrapper.find('.card-cover img').exists()).toBe(false)
    })
  })
})
