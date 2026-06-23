import { describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import TrackingDashboard from '../TrackingDashboard.vue'

const apiMock = vi.hoisted(() => ({
  getCalls: [],
}))

vi.mock('@element-plus/icons-vue', async (importOriginal) => {
  const actual = await importOriginal()
  const icon = (name) => ({ name, render: () => null })
  return {
    ...actual,
    Clock: actual.Clock || icon('Clock'),
    DataLine: actual.DataLine || icon('DataLine'),
    Delete: actual.Delete || icon('Delete'),
    Document: actual.Document || icon('Document'),
    Download: actual.Download || icon('Download'),
    Refresh: actual.Refresh || icon('Refresh'),
    Setting: actual.Setting || icon('Setting'),
    Timer: actual.Timer || icon('Timer'),
    TrendCharts: actual.TrendCharts || icon('TrendCharts'),
    User: actual.User || icon('User'),
    View: actual.View || icon('View'),
  }
})

vi.mock('@/api/client', () => ({
  get: (url, params) => {
    apiMock.getCalls.push({ url, params })
    if (url === '/admin/tracking/config') return Promise.resolve({ enable_tracking: 1 })
    if (url === '/admin/tracking/realtime') {
      return Promise.resolve({
        recent_visits: 1,
        online_sessions: 1,
        active_users: [],
        top_paths: [{ path: '/api/v1/projects/demo/files/preview', count: 3 }],
      })
    }
    if (url === '/admin/tracking/stats') {
      return Promise.resolve({
        total_visits: 10,
        unique_visitors: 5,
        device_distribution: [{ type: 'desktop', count: 8 }, { type: 'mobile', count: 2 }],
        browser_distribution: [{ name: 'Edge', count: 8 }, { name: 'Chrome Mobile WebView', count: 2 }],
        os_distribution: [{ name: 'Windows', count: 8 }, { name: 'Android', count: 2 }],
        trend: [{
          label: '2026-06-16',
          visits: 10,
          visitors: 5,
          avg_response_time_ms: 23,
          min_response_time_ms: 10,
          max_response_time_ms: 45,
          error_count: 1,
          error_rate: 10,
        }],
        country_distribution: [],
        status_distribution: [],
        response_time: { avg_ms: 20, min_ms: 10, max_ms: 30 },
      })
    }
    if (url === '/admin/tracking/logs') {
      return Promise.resolve({
        total: 2,
        items: [{
          id: 'log-1',
          timestamp: '2026-06-16T12:00:00.789123Z',
          ip_address: '127.0.0.1',
          visitor_id: 'visitor-abcdef-123456',
          is_page_view: true,
          geo_latitude: 39.904212,
          geo_longitude: 116.407389,
          geo_accuracy: 8.5,
          client_timezone: 'Asia/Shanghai',
          client_language: 'zh-CN',
          device_type: 'desktop',
          device_brand: 'Microsoft',
          device_model: 'PC',
          os_name: 'Windows',
          os_version: '11',
          browser_name: 'Edge',
          browser_version: '149',
          request_path: '/demo',
          response_status: 200,
          response_time_ms: 10,
        }, {
          id: 'log-2',
          timestamp: '2026-06-17T08:30:00.000000Z',
          ip_address: '10.0.0.2',
          visitor_id: 'visitor-firefox-654321',
          is_page_view: true,
          geo_latitude: 31.230416,
          geo_longitude: 121.473701,
          geo_accuracy: 12.2,
          client_timezone: 'UTC',
          client_language: 'en-US',
          device_type: 'mobile',
          device_brand: 'Google',
          device_model: 'Pixel 8',
          os_name: '',
          browser_name: 'Firefox',
          browser_version: '126',
          request_path: '/demo/mobile',
          response_status: 200,
          response_time_ms: 25,
        }],
      })
    }
    return Promise.resolve({})
  },
  put: () => Promise.resolve({}),
  del: () => Promise.resolve({ deleted_count: 0 }),
}))

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  props: ['modelValue', 'type', 'size', 'disabled', 'loading'],
  emits: ['click', 'update:modelValue', 'change'],
  setup(props, { slots, emit, attrs }) {
    return () => h(tag, {
      class: [name, attrs.class, props.type, props.size],
      disabled: props.disabled || props.loading || undefined,
      onClick: (event) => emit('click', event),
      onInput: (event) => emit('update:modelValue', event?.target?.value),
      onChange: (event) => emit('change', event),
    }, slots.default?.())
  },
})

const ElTableColumn = defineComponent({
  name: 'ElTableColumn',
  props: ['prop', 'label'],
  setup() {
    return () => null
  },
})

const ElTable = defineComponent({
  name: 'ElTable',
  props: ['data'],
  setup(props, { slots, attrs }) {
    return () => {
      const columns = (slots.default?.() || []).filter((vnode) => vnode && vnode.type)
      const header = h(
        'div',
        { class: 'el-table__header' },
        columns.map((column, columnIndex) => h(
          'div',
          { class: 'el-table__cell el-table__header-cell', 'data-column': columnIndex },
          column.props?.label ?? '',
        )),
      )
      const rows = (props.data || []).map((row, rowIndex) => h(
        'div',
        { class: 'el-table__row', 'data-row': rowIndex },
        columns.map((column, columnIndex) => {
          const cellSlot = column.children?.default
          const content = cellSlot ? cellSlot({ row, $index: rowIndex }) : row[column.props?.prop] ?? ''
          return h('div', { class: 'el-table__cell', 'data-column': columnIndex }, content)
        }),
      ))
      return h('div', { class: ['el-table', attrs.class] }, [header, rows])
    }
  },
})

const ElCard = defineComponent({
  name: 'ElCard',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('div', { class: ['el-card', attrs.class] }, [slots.header?.(), slots.default?.()])
  },
})

const ElDialog = defineComponent({
  name: 'ElDialog',
  inheritAttrs: false,
  props: ['modelValue', 'title'],
  emits: ['update:modelValue'],
  setup(props, { slots, attrs }) {
    return () => {
      if (!props.modelValue) return null
      return h('div', { class: ['el-dialog', attrs.class] }, [
        h('div', { class: 'el-dialog__title' }, props.title),
        h('div', { class: 'el-dialog__body' }, slots.default?.()),
        slots.footer?.(),
      ])
    }
  },
})

const ElDescriptions = defineComponent({
  name: 'ElDescriptions',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('div', { class: ['el-descriptions', attrs.class] }, slots.default?.())
  },
})

const ElDescriptionsItem = defineComponent({
  name: 'ElDescriptionsItem',
  props: ['label'],
  setup(props, { slots }) {
    return () => h('div', { class: 'el-descriptions-item' }, [
      h('strong', { class: 'el-descriptions-item__label' }, props.label),
      h('span', { class: 'el-descriptions-item__content' }, slots.default?.()),
    ])
  },
})

const ElDivider = defineComponent({
  name: 'ElDivider',
  setup(_, { slots }) {
    return () => h('div', { class: 'el-divider' }, slots.default?.())
  },
})

describe('TrackingDashboard', () => {
  it('merges access columns into a clickable info card and opens a details dialog', async () => {
    apiMock.getCalls.length = 0
    const wrapper = mount(TrackingDashboard, {
      global: {
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
        },
        components: {
          ElRow: passthrough('ElRow'),
          ElCol: passthrough('ElCol'),
          ElCard,
          ElButton: passthrough('ElButton', 'button'),
          ElRadioGroup: passthrough('ElRadioGroup'),
          ElRadioButton: passthrough('ElRadioButton', 'button'),
          ElSelect: passthrough('ElSelect'),
          ElOption: passthrough('ElOption', 'option'),
          ElTag: passthrough('ElTag', 'span'),
          ElSwitch: passthrough('ElSwitch', 'input'),
          ElSlider: passthrough('ElSlider', 'input'),
          ElInput: passthrough('ElInput', 'input'),
          ElDatePicker: passthrough('ElDatePicker', 'input'),
          ElPagination: passthrough('ElPagination'),
          ElInputNumber: passthrough('ElInputNumber', 'input'),
          ElTable,
          ElTableColumn,
          ElDialog,
          ElDescriptions,
          ElDescriptionsItem,
          ElDivider,
        },
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.top-paths--wide').exists()).toBe(true)
    expect(wrapper.find('.top-paths--wide .realtime-path-table').exists()).toBe(true)
    expect(wrapper.find('.distribution-browser-card').exists()).toBe(true)
    expect(wrapper.find('.environment-grid').exists()).toBe(true)
    expect(wrapper.findAll('.environment-card')).toHaveLength(3)
    expect(wrapper.find('.trend-card').exists()).toBe(true)
    expect(wrapper.find('.trend-card .trend-table-full').exists()).toBe(true)
    expect(wrapper.text()).toContain('平均响应')
    expect(wrapper.text()).toContain('错误率')
    expect(wrapper.text()).toContain('10%')
    expect(wrapper.text()).not.toContain('???')

    const tableHeaders = wrapper.findAll('.logs-table .el-table__header-cell').map((cell) => cell.text())
    expect(tableHeaders).toContain('访问信息')
    expect(tableHeaders).not.toContain('设备')
    expect(tableHeaders).not.toContain('系统')
    expect(tableHeaders).not.toContain('浏览器')
    expect(tableHeaders).not.toContain('位置')
    expect(tableHeaders).not.toContain('环境')

    const card = wrapper.find('.tracking-info-card')
    expect(card.exists()).toBe(true)
    expect(card.attributes('role')).toBe('button')
    expect(card.text()).toContain('桌面端')
    expect(card.text()).toContain('Windows PC')
    expect(card.text()).toContain('Windows 11 · Edge 149')
    expect(card.text()).toContain('📍 39.9042, 116.4074 (±9m)')
    expect(card.text()).toContain('Asia/Shanghai · zh-CN')
    expect(wrapper.text()).toContain('visitor-…')
    expect(wrapper.find('.access-info-dialog').exists()).toBe(false)

    const date = new Date('2026-06-16T12:00:00.789123Z')
    const pad = (number) => String(number).padStart(2, '0')
    const expectedLogTime = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`

    await card.trigger('click')
    await flushPromises()

    const dialog = wrapper.find('.access-info-dialog')
    expect(dialog.exists()).toBe(true)
    expect(dialog.text()).toContain('访问信息详情')
    expect(dialog.text()).toContain('桌面端')
    expect(dialog.text()).toContain('Windows PC')
    expect(dialog.text()).toContain(expectedLogTime)
    expect(dialog.text()).toContain('设备')
    expect(dialog.text()).toContain('系统')
    expect(dialog.text()).toContain('Windows 11')
    expect(dialog.text()).toContain('浏览器')
    expect(dialog.text()).toContain('Edge 149')
    expect(dialog.text()).toContain('位置')
    expect(dialog.text()).toContain('📍 39.9042, 116.4074 (±9m)')
    expect(dialog.text()).toContain('环境')
    expect(dialog.text()).toContain('Asia/Shanghai · zh-CN')
    expect(dialog.text()).toContain('访客 ID')
    expect(dialog.text()).toContain('visitor-abcdef-123456')

    expect(wrapper.text()).not.toContain('2026-06-16T12:00:00.789123Z')
    expect(wrapper.text()).not.toContain('.789123')

    const logsCall = apiMock.getCalls.find((call) => call.url === '/admin/tracking/logs')
    expect(logsCall?.params?.page_views_only).toBe(1)
  })

  it('shows full browser name and version in dialog when os is missing', async () => {
    apiMock.getCalls.length = 0
    const wrapper = mount(TrackingDashboard, {
      global: {
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
        },
        components: {
          ElRow: passthrough('ElRow'),
          ElCol: passthrough('ElCol'),
          ElCard,
          ElButton: passthrough('ElButton', 'button'),
          ElRadioGroup: passthrough('ElRadioGroup'),
          ElRadioButton: passthrough('ElRadioButton', 'button'),
          ElSelect: passthrough('ElSelect'),
          ElOption: passthrough('ElOption', 'option'),
          ElTag: passthrough('ElTag', 'span'),
          ElSwitch: passthrough('ElSwitch', 'input'),
          ElSlider: passthrough('ElSlider', 'input'),
          ElInput: passthrough('ElInput', 'input'),
          ElDatePicker: passthrough('ElDatePicker', 'input'),
          ElPagination: passthrough('ElPagination'),
          ElInputNumber: passthrough('ElInputNumber', 'input'),
          ElTable,
          ElTableColumn,
          ElDialog,
          ElDescriptions,
          ElDescriptionsItem,
          ElDivider,
        },
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    const cards = wrapper.findAll('.tracking-info-card')
    expect(cards).toHaveLength(2)

    await cards[1].trigger('click')
    await flushPromises()

    const dialog = wrapper.find('.access-info-dialog')
    expect(dialog.exists()).toBe(true)
    const summaryItems = dialog.findAll('.access-info-summary .el-descriptions-item')
    const browserItem = summaryItems.find((item) => item.find('.el-descriptions-item__label').text() === '浏览器')
    expect(browserItem?.find('.el-descriptions-item__content').text()).toBe('Firefox 126')
  })

  it('shows os name and version together in dialog system summary without extra spaces', async () => {
    apiMock.getCalls.length = 0
    const wrapper = mount(TrackingDashboard, {
      global: {
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
        },
        components: {
          ElRow: passthrough('ElRow'),
          ElCol: passthrough('ElCol'),
          ElCard,
          ElButton: passthrough('ElButton', 'button'),
          ElRadioGroup: passthrough('ElRadioGroup'),
          ElRadioButton: passthrough('ElRadioButton', 'button'),
          ElSelect: passthrough('ElSelect'),
          ElOption: passthrough('ElOption', 'option'),
          ElTag: passthrough('ElTag', 'span'),
          ElSwitch: passthrough('ElSwitch', 'input'),
          ElSlider: passthrough('ElSlider', 'input'),
          ElInput: passthrough('ElInput', 'input'),
          ElDatePicker: passthrough('ElDatePicker', 'input'),
          ElPagination: passthrough('ElPagination'),
          ElInputNumber: passthrough('ElInputNumber', 'input'),
          ElTable,
          ElTableColumn,
          ElDialog,
          ElDescriptions,
          ElDescriptionsItem,
          ElDivider,
        },
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    await wrapper.find('.tracking-info-card').trigger('click')
    await flushPromises()

    const summaryItems = wrapper.findAll('.access-info-summary .el-descriptions-item')
    const systemItem = summaryItems.find((item) => item.find('.el-descriptions-item__label').text() === '系统')
    expect(systemItem?.find('.el-descriptions-item__content').text()).toBe('Windows 11')
  })

})
