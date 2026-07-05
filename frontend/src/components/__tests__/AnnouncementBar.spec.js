import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AnnouncementBar from '../common/AnnouncementBar.vue'

const getMock = vi.fn()
const eventChannel = vi.hoisted(() => ({
  options: null,
}))

vi.mock('@/api/client', () => ({
  get: (...args) => getMock(...args),
}))

vi.mock('@/composables/useEventChannel', () => ({
  useEventChannel: (options) => {
    eventChannel.options = options
    return {
      connected: { value: false },
      lastEvent: { value: null },
      error: { value: null },
      restart: vi.fn(),
      stop: vi.fn(),
    }
  },
}))

function mountAnnouncementBar() {
  return mount(AnnouncementBar, {
    global: {
      stubs: {
        'el-dialog': { template: '<div class="dialog-stub"><slot /><slot name="footer" /></div>' },
      },
    },
  })
}

describe('AnnouncementBar', () => {
  beforeEach(() => {
    getMock.mockReset()
    sessionStorage.clear()
    eventChannel.options = null
  })

  it('renders a duplicated seamless track for scroll announcements', async () => {
    getMock.mockResolvedValue([
      { id: '1', title: '维护通知', content: '今晚 22:00 升级', display_mode: 'scroll' },
      { id: '2', title: '系统公告', content: '请及时保存文档', display_mode: 'scroll' },
    ])

    const wrapper = mountAnnouncementBar()
    await flushPromises()

    const groups = wrapper.findAll('.scroll-group')
    expect(groups).toHaveLength(2)
    expect(groups[0].text()).toContain('维护通知')
    expect(groups[1].text()).toContain('维护通知')
    expect(wrapper.find('.scroll-track').classes()).not.toContain('is-static')
    expect(wrapper.find('.scroll-track').attributes('style')).toContain('--scroll-duration')
  })

  it('keeps even one short scroll announcement moving', async () => {
    getMock.mockResolvedValue([
      { id: '1', title: '注意', content: '请及时查看', display_mode: 'scroll' },
    ])

    const wrapper = mountAnnouncementBar()
    await flushPromises()

    const groups = wrapper.findAll('.scroll-group')
    expect(groups).toHaveLength(2)
    expect(wrapper.find('.scroll-track').classes()).not.toContain('is-static')
    expect(wrapper.find('.scroll-track').attributes('style')).toContain('--scroll-duration')
    expect(wrapper.text()).toContain('公告注意: 请及时查看')
  })

  it('renders readable scroll and popup copy without mojibake symbols', async () => {
    getMock.mockResolvedValue([
      { id: '1', title: '注意', content: '请及时查看', display_mode: 'scroll' },
      { id: '2', title: '弹窗', content: '请查看说明', display_mode: 'popup' },
    ])

    const wrapper = mountAnnouncementBar()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('公告注意: 请及时查看')
    expect(text).toContain('我知道了')
    expect(text).not.toContain('??')
    expect(text).not.toContain('📣')
    expect(text).not.toContain('·')
    expect(text).not.toContain('馃')
    expect(text).not.toContain('鎴戜')
    expect(text).not.toContain(' 路 ')
  })

  it('reloads active announcements when an announcements event arrives', async () => {
    getMock
      .mockResolvedValueOnce([
        { id: '1', title: '注意', content: '请及时查看', display_mode: 'scroll' },
      ])
      .mockResolvedValueOnce([
        { id: '2', title: '新公告', content: '已刷新', display_mode: 'scroll' },
      ])

    const wrapper = mountAnnouncementBar()
    await flushPromises()

    await eventChannel.options.onEvent({
      event: 'announcement.updated',
      data: {
        topic: 'announcements',
        type: 'announcement.updated',
        payload: { announcement_id: '2' },
      },
    })
    await flushPromises()

    expect(getMock).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('新公告: 已刷新')
  })
})
