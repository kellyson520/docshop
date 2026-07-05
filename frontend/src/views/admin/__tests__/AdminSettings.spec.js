import { shallowMount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

let AdminSettings

const mocks = {
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
  settingsStore: {
    userSettings: {},
    fetchSettings: vi.fn(),
    fetchDevices: vi.fn(),
    updateSettings: vi.fn(),
    changePassword: vi.fn(),
    logoutDevice: vi.fn(),
    logoutAllDevices: vi.fn(),
  },
  authStore: {
    user: null,
  },
  eventChannel: {
    options: null,
  },
}

function resetStoreState() {
  mocks.settingsStore.userSettings = {
    profile: { username: 'admin', avatar: '' },
    notifications: { email: true, push: true },
    appearance: { theme: 'system', default_page_size: 20 },
    tracking: {
      enabled: true,
      ip_tracking: true,
      device_tracking: true,
      location_tracking: false,
    },
  }
  mocks.authStore.user = { username: 'admin', avatar: '' }
}

const passthrough = (template = '<div><slot /></div>') => ({ template })

function mountAdminSettings() {
  return shallowMount(AdminSettings, {
    global: {
      renderStubDefaultSlot: true,
      stubs: {
        PageHeader: passthrough('<header><slot name="actions" /><slot /></header>'),
        ElSkeleton: passthrough(),
        ElCard: passthrough(),
        ElTabs: passthrough(),
        ElTabPane: passthrough(),
        ElForm: passthrough('<form><slot /></form>'),
        ElFormItem: {
          props: ['label'],
          template: '<div><label v-if="label">{{ label }}</label><slot /></div>',
        },
        ElSwitch: passthrough('<button><slot /></button>'),
        ElInput: passthrough('<input />'),
        ElInputNumber: passthrough('<input />'),
        ElSelect: passthrough('<select><slot /></select>'),
        ElOption: passthrough('<option />'),
        ElRadioGroup: passthrough('<div><slot /></div>'),
        ElRadio: passthrough('<label><slot /></label>'),
        ElButton: passthrough('<button @click="$emit(\'click\')"><slot /></button>'),
        ElDivider: passthrough('<hr />'),
        ElAvatar: passthrough('<span><slot /></span>'),
        ElUpload: passthrough('<div><slot /></div>'),
        ElEmpty: passthrough('<div />'),
        ElTag: passthrough('<span><slot /></span>'),
        ElIcon: passthrough('<i><slot /></i>'),
      },
    },
  })
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('AdminSettings security settings', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()
    vi.useRealTimers()

    resetStoreState()
    mocks.eventChannel.options = null
    mocks.settingsStore.fetchSettings.mockResolvedValue({})
    mocks.settingsStore.fetchDevices.mockResolvedValue([])
    mocks.apiGet.mockResolvedValue({
      force_https: false,
      cors_origins: ['http://localhost:5173'],
      rate_upload: 120,
      token_expire: 1440,
      max_file_mb: 50,
      log_level: 'INFO',
      file_types: ['.pdf', '.docx'],
    })
    mocks.apiPut.mockResolvedValue({})

    vi.doMock('@/api/client', () => ({
      get: mocks.apiGet,
      put: mocks.apiPut,
    }))

    vi.doMock('@/api/settings', () => ({
      uploadAvatar: vi.fn(),
    }))

    vi.doMock('@/stores/settings', () => ({
      useSettingsStore: () => mocks.settingsStore,
    }))

    vi.doMock('@/stores/auth', () => ({
      useAuthStore: () => mocks.authStore,
    }))

    vi.doMock('@/composables/useMessage', () => ({
      useMessage: () => ({
        success: mocks.messageSuccess,
        error: mocks.messageError,
      }),
    }))

    vi.doMock('@/composables/useEventChannel', () => ({
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

    AdminSettings = (await import('../AdminSettings.vue')).default
  })

  it('saves only the real global rate limit field', async () => {
    const wrapper = mountAdminSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('请求限速')
    expect(wrapper.text()).not.toContain('API 限速')

    const securityConfig = getExpose(wrapper, 'securityConfig')
    securityConfig.rate_upload = 321
    securityConfig.rate_api = 9999

    const handleSaveSecurity = getExpose(wrapper, 'handleSaveSecurity')
    await handleSaveSecurity()

    expect(mocks.apiPut).toHaveBeenCalledWith('/settings', expect.objectContaining({
      rate_upload: 321,
    }))
    expect(mocks.apiPut.mock.calls[0][1]).not.toHaveProperty('rate_api')
  })

  it('reloads latest backend values after saving security settings', async () => {
    mocks.apiGet
      .mockResolvedValueOnce({
        force_https: false,
        cors_origins: ['http://localhost:5173'],
        rate_upload: 120,
        token_expire: 1440,
        max_file_mb: 50,
        log_level: 'INFO',
        file_types: ['.pdf'],
      })
      .mockResolvedValueOnce({
        force_https: true,
        cors_origins: ['https://admin.example.com'],
        rate_upload: 321,
        token_expire: 60,
        max_file_mb: 64,
        log_level: 'WARNING',
        file_types: ['.pdf', '.docx'],
      })

    const wrapper = mountAdminSettings()
    await flushPromises()

    const handleTabChange = getExpose(wrapper, 'handleTabChange')
    await handleTabChange('security')
    await flushPromises()

    const securityConfig = getExpose(wrapper, 'securityConfig')
    securityConfig.force_https = true
    securityConfig.rate_upload = 321
    securityConfig.token_expire = 60
    securityConfig.max_file_mb = 64
    securityConfig.log_level = 'DEBUG'
    securityConfig.file_types_str = '.pdf, .docx'

    const handleSaveSecurity = getExpose(wrapper, 'handleSaveSecurity')
    await handleSaveSecurity()
    await flushPromises()

    expect(mocks.apiPut).toHaveBeenCalledWith('/settings', expect.objectContaining({
      force_https: true,
      rate_upload: 321,
      token_expire: 60,
      max_file_mb: 64,
      log_level: 'DEBUG',
      file_types: ['.pdf', '.docx'],
    }))
    expect(mocks.apiGet).toHaveBeenCalledTimes(2)
    expect(securityConfig.log_level).toBe('WARNING')
    expect(securityConfig.cors_origins_str).toBe('https://admin.example.com')
    expect(ElMessage.success).toHaveBeenCalledWith('运行期配置已写入 .env 并立即生效')
  })

  it('does not start polling and refreshes on config.updated event', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval')
    mocks.apiGet
      .mockResolvedValueOnce({
        force_https: false,
        cors_origins: ['http://localhost:5173'],
        rate_upload: 120,
        token_expire: 1440,
        max_file_mb: 50,
        log_level: 'INFO',
        file_types: ['.pdf'],
      })
      .mockResolvedValueOnce({
        force_https: true,
        cors_origins: ['https://changed.example.com'],
        rate_upload: 88,
        token_expire: 30,
        max_file_mb: 10,
        log_level: 'ERROR',
        file_types: ['.pdf', '.xlsx'],
      })

    const wrapper = mountAdminSettings()
    await flushPromises()

    const handleTabChange = getExpose(wrapper, 'handleTabChange')
    await handleTabChange('security')
    await flushPromises()

    const securityConfig = getExpose(wrapper, 'securityConfig')
    expect(securityConfig.log_level).toBe('INFO')
    expect(setIntervalSpy).not.toHaveBeenCalled()

    await mocks.eventChannel.options.onEvent({
      event: 'config.updated',
      data: {
        topic: 'config',
        type: 'config.updated',
      },
    })
    await flushPromises()

    expect(mocks.apiGet).toHaveBeenCalledTimes(2)
    expect(securityConfig.log_level).toBe('ERROR')
    expect(securityConfig.cors_origins_str).toBe('https://changed.example.com')

    wrapper.unmount()
    setIntervalSpy.mockRestore()
  })
})
