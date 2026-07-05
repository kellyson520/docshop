import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AnnouncementManager from '../AnnouncementManager.vue'

const mocks = vi.hoisted(() => ({
  listAnnouncements: vi.fn(),
  createAnnouncement: vi.fn(),
  updateAnnouncement: vi.fn(),
  deleteAnnouncement: vi.fn(),
  eventChannel: {
    options: null,
  },
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
  messageWarning: vi.fn(),
  confirm: vi.fn(),
}))

vi.mock('@/api/announcement', () => ({
  listAnnouncements: mocks.listAnnouncements,
  createAnnouncement: mocks.createAnnouncement,
  updateAnnouncement: mocks.updateAnnouncement,
  deleteAnnouncement: mocks.deleteAnnouncement,
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: mocks.messageSuccess,
    error: mocks.messageError,
    warning: mocks.messageWarning,
  },
  ElMessageBox: {
    confirm: mocks.confirm,
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  Plus: { template: '<i />' },
}))

vi.mock('@/composables/useEventChannel', () => ({
  useEventChannel: (options) => {
    mocks.eventChannel.options = options
    return {
      connected: { value: false },
      lastEvent: { value: null },
      error: { value: null },
      restart: vi.fn(),
      stop: vi.fn(),
    }
  },
}))

const globalMountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      PageHeader: { template: '<div><slot name="actions" /></div>' },
      ElButton: { template: '<button @click="$emit(\'click\')"><slot /></button>' },
      ElCard: { template: '<div><slot name="header" /><slot /></div>' },
      ElTable: { template: '<div><slot /></div>' },
      ElTableColumn: { template: '<div><slot :row="{}" /></div>' },
      ElTag: { template: '<span><slot /></span>' },
      ElSwitch: { template: '<input type="checkbox" />' },
      ElPagination: { template: '<div />' },
      ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
      ElForm: { template: '<form><slot /></form>' },
      ElFormItem: { template: '<div><slot /></div>' },
      ElInput: { template: '<input />' },
      ElSelect: { template: '<div><slot /></div>' },
      ElOption: { template: '<div />' },
      ElInputNumber: { template: '<input />' },
      AnnouncementRenderer: { template: '<div />' },
    },
    directives: { loading: {} },
  },
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('AnnouncementManager rich blocks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.eventChannel.options = null
    mocks.listAnnouncements.mockResolvedValue({ items: [], total: 0 })
    mocks.createAnnouncement.mockResolvedValue({ id: 'ann-1' })
    mocks.updateAnnouncement.mockResolvedValue({})
  })

  it('submits content_blocks when creating an announcement', async () => {
    const wrapper = mount(AnnouncementManager, globalMountOptions)
    await flushPromises()

    const form = getExpose(wrapper, 'form')
    form.value.title = '升级通知'
    form.value.content = '夜间发布'
    form.value.content_blocks = [
      { type: 'paragraph', text: 'Deploy at 22:00' },
      { type: 'code', language: 'bash', content: 'docker compose up -d' },
    ]

    await getExpose(wrapper, 'handleSave')()

    expect(mocks.createAnnouncement).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '升级通知',
        content_blocks: expect.arrayContaining([
          expect.objectContaining({ type: 'paragraph' }),
          expect.objectContaining({ type: 'code' }),
        ]),
      }),
    )
  })

  it('reloads the list when an announcements event arrives', async () => {
    mocks.listAnnouncements
      .mockResolvedValueOnce({ items: [{ id: 'ann-1', title: '旧公告', content: 'before' }], total: 1 })
      .mockResolvedValueOnce({ items: [{ id: 'ann-2', title: '新公告', content: 'after' }], total: 1 })

    const wrapper = mount(AnnouncementManager, globalMountOptions)
    await flushPromises()

    await mocks.eventChannel.options.onEvent({
      event: 'announcement.updated',
      data: {
        topic: 'announcements',
        type: 'announcement.updated',
        payload: { announcement_id: 'ann-2' },
      },
    })
    await flushPromises()

    const items = getExpose(wrapper, 'items')
    const resolvedItems = Array.isArray(items) ? items : items.value
    expect(mocks.listAnnouncements).toHaveBeenCalledTimes(2)
    expect(resolvedItems[0].title).toBe('新公告')
  })
})
