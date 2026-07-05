import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AnnouncementPreviewDialog from '../AnnouncementPreviewDialog.vue'

describe('AnnouncementPreviewDialog', () => {
  it('renders rich blocks through AnnouncementRenderer', () => {
    const wrapper = mount(AnnouncementPreviewDialog, {
      props: {
        modelValue: true,
        title: '升级通知',
        blocks: [
          { type: 'paragraph', text: 'Deploy at 22:00' },
          { type: 'button', label: '查看详情', url: '/docs/deploy' },
        ],
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
          ElButton: { template: '<button><slot /></button>' },
        },
      },
    })

    expect(wrapper.text()).toContain('升级通知')
    expect(wrapper.text()).toContain('Deploy at 22:00')
    expect(wrapper.text()).toContain('查看详情')
  })

  it('falls back to plain text content when blocks are empty', () => {
    const wrapper = mount(AnnouncementPreviewDialog, {
      props: {
        modelValue: true,
        title: '纯文本公告',
        blocks: [],
        fallbackContent: '今晚 22:00 发布',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
          ElButton: { template: '<button><slot /></button>' },
        },
      },
    })

    expect(wrapper.text()).toContain('今晚 22:00 发布')
  })
})
