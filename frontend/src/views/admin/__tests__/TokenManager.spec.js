import fs from 'node:fs'
import path from 'node:path'
import { defineComponent, h } from 'vue'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'

import TokenManager from '../TokenManager.vue'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
  listShareTokens: vi.fn(),
  getSharePolicy: vi.fn(),
  updateShareToken: vi.fn(),
  regenerateShareToken: vi.fn(),
  deleteShareToken: vi.fn(),
  updateSharePolicy: vi.fn(),
  copyToClipboard: vi.fn(() => Promise.resolve(true)),
  buildShareUrl: vi.fn((token, origin) => `${origin}/s/${token}`),
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  confirm: vi.fn(),
  alert: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  get: mocks.get,
  post: mocks.post,
  put: mocks.put,
  del: mocks.del,
}))

vi.mock('@/api/share', () => ({
  listShareTokens: mocks.listShareTokens,
  getSharePolicy: mocks.getSharePolicy,
  updateShareToken: mocks.updateShareToken,
  regenerateShareToken: mocks.regenerateShareToken,
  deleteShareToken: mocks.deleteShareToken,
  updateSharePolicy: mocks.updateSharePolicy,
}))

vi.mock('@/utils', () => ({
  copyToClipboard: mocks.copyToClipboard,
}))

vi.mock('@/utils/previewManagement', () => ({
  buildShareUrl: mocks.buildShareUrl,
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: mocks.success,
    error: mocks.error,
    warning: mocks.warning,
  },
  ElMessageBox: {
    confirm: mocks.confirm,
    alert: mocks.alert,
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  CopyDocument: { template: '<i />' },
  Delete: { template: '<i />' },
  Lock: { template: '<i />' },
  Plus: { template: '<i />' },
  Refresh: { template: '<i />' },
}))

function passthrough(name, tag = 'div') {
  return defineComponent({
    name,
    inheritAttrs: false,
    setup(_, { slots, attrs }) {
      return () => h(tag, attrs, slots.default?.())
    },
  })
}

const ElDialog = defineComponent({
  name: 'ElDialog',
  inheritAttrs: false,
  props: {
    modelValue: { type: Boolean, default: false },
    title: { type: String, default: '' },
    appendToBody: { type: Boolean, default: false },
    alignCenter: { type: Boolean, default: false },
  },
  setup(props, { slots, attrs }) {
    return () => {
      if (!props.modelValue) return null
      return h(
        'section',
        {
          class: ['el-dialog', attrs.class],
          'data-append-to-body': String(props.appendToBody),
          'data-align-center': String(props.alignCenter),
        },
        [
          h('header', { class: 'el-dialog__title' }, props.title),
          h('div', { class: 'el-dialog__body' }, slots.default?.()),
          slots.footer?.(),
        ],
      )
    }
  },
})

const globalMountOptions = {
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      PageHeader: { template: '<div><slot name="actions" /><slot /></div>' },
      ElCard: { template: '<div><slot /></div>' },
      ElTabs: { template: '<div><slot /></div>' },
      ElTabPane: { template: '<div><slot /></div>' },
      ElTable: { template: '<div><slot /></div>' },
      ElTableColumn: { template: '<div />' },
      ElAvatar: { template: '<div><slot /></div>' },
      ElTooltip: { template: '<div><slot /></div>' },
      ElSegmented: { template: '<div />' },
      ElDialog,
      ElForm: { template: '<form><slot /></form>' },
      ElFormItem: { template: '<div><slot /></div>' },
      ElInput: passthrough('ElInput', 'input'),
      ElInputNumber: passthrough('ElInputNumber', 'input'),
      ElSwitch: passthrough('ElSwitch', 'input'),
      ElDatePicker: passthrough('ElDatePicker', 'input'),
      ElSelect: passthrough('ElSelect'),
      ElOption: passthrough('ElOption', 'option'),
      ElCheckboxGroup: { template: '<div><slot /></div>' },
      ElCheckbox: passthrough('ElCheckbox', 'label'),
      ElButton: {
        template: '<button @click="$emit(\'click\')"><slot /></button>',
      },
      ElIcon: { template: '<i><slot /></i>' },
    },
    directives: { loading: {} },
  },
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function createShareTokenRow(overrides = {}) {
  return {
    id: 'share-token-1',
    name: 'Share file token',
    resource_type: 'file',
    resource_id: 'file-1',
    allow_download: true,
    require_login: true,
    password_hint: 'Dept code',
    allow_preview: false,
    allow_diff: true,
    allow_versions: false,
    policy_mode: 'override_with_token_policy',
    max_views: 8,
    max_downloads: 3,
    expires_at: '2026-07-08T10:20:30Z',
    ...overrides,
  }
}

describe('TokenManager share token editor', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mocks.get.mockImplementation((url) => {
      if (url === '/users') {
        return Promise.resolve({ items: [], stats: { total: 0, admins: 0, users: 0 } })
      }
      if (url === '/users/settings/registration') {
        return Promise.resolve({ registration_enabled: false })
      }
      return Promise.resolve({})
    })
    mocks.listShareTokens.mockResolvedValue({ items: [] })
    mocks.getSharePolicy.mockResolvedValue({
      enabled: true,
      allow_user_creation: true,
      allow_anonymous_creation: false,
      allowed_resource_types: ['project', 'file', 'version'],
      default_max_views: 0,
      default_max_downloads: 0,
      default_allow_download: true,
      max_expiry_days: 0,
    })
    mocks.updateShareToken.mockResolvedValue({})
    mocks.updateSharePolicy.mockResolvedValue({})
  })

  it('shows aligned share-access controls when opening the share token editor', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    getExpose(wrapper, 'openShareTokenEditor')(createShareTokenRow())
    await flushPromises()

    const dialog = wrapper.find('.el-dialog')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('data-append-to-body')).toBe('true')
    expect(dialog.attributes('data-align-center')).toBe('true')

    const form = getExpose(wrapper, 'shareTokenForm')
    expect(form).toMatchObject({
      require_login: true,
      password: '',
      clear_password: false,
      password_hint: 'Dept code',
      allow_preview: false,
      allow_diff: true,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
    })
  })

  it('submits aligned share access fields without clearing password implicitly', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    getExpose(wrapper, 'openShareTokenEditor')(createShareTokenRow())
    const form = getExpose(wrapper, 'shareTokenForm')
    form.name = 'Updated share token'
    form.max_views = 12
    form.max_downloads = 6
    form.allow_download = false
    form.require_login = false
    form.password = ''
    form.clear_password = false
    form.password_hint = 'New hint'
    form.allow_preview = true
    form.allow_diff = false
    form.allow_versions = true
    form.policy_mode = 'inherit_resource_policy'
    form.expires_at = '2026-07-09T08:09:10'

    await getExpose(wrapper, 'saveShareToken')()

    expect(mocks.updateShareToken).toHaveBeenCalledWith('share-token-1', {
      name: 'Updated share token',
      max_views: 12,
      max_downloads: 6,
      allow_download: false,
      require_login: false,
      password_hint: 'New hint',
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-09T08:09:10Z',
    })
  })

  it('can explicitly clear an existing password', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    getExpose(wrapper, 'openShareTokenEditor')(createShareTokenRow())
    const form = getExpose(wrapper, 'shareTokenForm')
    form.clear_password = true

    await getExpose(wrapper, 'saveShareToken')()

    expect(mocks.updateShareToken).toHaveBeenCalledWith(
      'share-token-1',
      expect.objectContaining({
        password: '',
      }),
    )
  })

  it('sends a new password when one is provided', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    getExpose(wrapper, 'openShareTokenEditor')(createShareTokenRow())
    const form = getExpose(wrapper, 'shareTokenForm')
    form.password = 'NewPass#2026'

    await getExpose(wrapper, 'saveShareToken')()

    expect(mocks.updateShareToken).toHaveBeenCalledWith(
      'share-token-1',
      expect.objectContaining({
        password: 'NewPass#2026',
      }),
    )
  })

  it('reuses aligned share-access summary items for the share token list', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    const summaryItems = getExpose(wrapper, 'shareAccessSummaryItems')(createShareTokenRow({
      allow_download: false,
    }))

    expect(summaryItems.map((item) => item.key)).toEqual([
      'require_login',
      'password_hint',
      'allow_download',
      'allow_preview',
      'allow_diff',
      'allow_versions',
      'policy_mode',
    ])
  })

  it('opens a read-only restriction detail dialog instead of rendering every limit inline', async () => {
    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    const row = createShareTokenRow({
      view_count: 2,
      download_count: 1,
    })

    getExpose(wrapper, 'openShareRestrictionDialog')(row)
    await flushPromises()

    expect(getExpose(wrapper, 'shareRestrictionDialogVisible')).toBe(true)
    expect(getExpose(wrapper, 'shareRestrictionTarget')).toMatchObject(row)
    expect(getExpose(wrapper, 'shareRestrictionSummaryItems').map((item) => item.key)).toEqual([
      'require_login',
      'password_hint',
      'allow_download',
      'allow_preview',
      'allow_diff',
      'allow_versions',
      'policy_mode',
    ])

    const source = fs.readFileSync(path.resolve(__dirname, '../TokenManager.vue'), 'utf-8')
    expect(source).toContain('openShareRestrictionDialog')
    expect(source).toContain('shareRestrictionDialogVisible')
  })

  it('shows fixed independent share-permission copy instead of a runtime policy-mode selector', async () => {
    const source = fs.readFileSync(path.resolve(__dirname, '../TokenManager.vue'), 'utf-8')

    expect(source).toContain('分享权限仅作用于分享链接，不继承公开浏览权限。')
    expect(source).not.toContain('label="策略模式"')
    expect(source).not.toContain('sharePolicyModeOptions')
  })

  it('keeps the latest registration switch state when the initial fetch resolves late', async () => {
    const registrationRequest = createDeferred()
    mocks.get.mockImplementation((url) => {
      if (url === '/users') {
        return Promise.resolve({ items: [], stats: { total: 0, admins: 0, users: 0 } })
      }
      if (url === '/users/settings/registration') {
        return registrationRequest.promise
      }
      return Promise.resolve({})
    })
    mocks.put.mockResolvedValue({ registration_enabled: true })

    const wrapper = shallowMount(TokenManager, globalMountOptions)
    await flushPromises()

    wrapper.vm.registrationEnabled = true
    await getExpose(wrapper, 'saveRegistrationSwitch')()
    expect(wrapper.vm.registrationEnabled).toBe(true)

    registrationRequest.resolve({ registration_enabled: false })
    await flushPromises()

    expect(wrapper.vm.registrationEnabled).toBe(true)
  })
})
