import { defineStore } from 'pinia'
import {
  getUserSettings,
  updateUserSettings,
  changePassword,
  getLoginDevices,
  logoutDevice as logoutDeviceApi,
  logoutAllDevices as logoutAllDevicesApi
} from '@/api/settings'
import { useMessage } from '@/composables/useMessage'
import { applyMotionPreference, normalizeMotionMode } from '@/utils/motionPreference'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    /**
     * 用户设置数据
     */
    userSettings: {
      profile: {
        username: '',
        avatar: ''
      },
      notifications: {
        email: true,
        push: true
      },
      appearance: {
        theme: 'system',
        default_page_size: 20,
        motion_mode: 'system'
      },
      tracking: {
        enabled: true,
        ip_tracking: true,
        device_tracking: true,
        location_tracking: false
      }
    },

    /**
     * 登录设备列表
     */
    devices: [],

    /**
     * 设置加载状态
     */
    loading: false,

    /**
     * 设备加载状态
     */
    devicesLoading: false
  }),

  getters: {
    /**
     * 获取当前主题
     */
    currentTheme: (state) => state.userSettings.appearance?.theme || 'system',

    /**
     * 获取默认每页条数
     */
    defaultPageSize: (state) => state.userSettings.appearance?.default_page_size || 20,

    motionMode: (state) => normalizeMotionMode(state.userSettings.appearance?.motion_mode),

    /**
     * 检查追踪是否启用
     */
    isTrackingEnabled: (state) => state.userSettings.tracking?.enabled || false,

    /**
     * 获取用户显示名称
     */
    displayName: (state) => state.userSettings.profile?.username || '用户'
  },

  actions: {
    /**
     * 获取用户设置
     * @returns {Promise<Object>}
     */
    async fetchSettings() {
      this.loading = true
      try {
        const data = await getUserSettings()
        // 合并默认设置与服务器返回的设置
        this.userSettings = {
          profile: {
            username: data.profile?.username || '',
            avatar: data.profile?.avatar || ''
          },
          notifications: {
            email: data.notifications?.email ?? true,
            push: data.notifications?.push ?? true
          },
          appearance: {
            theme: data.appearance?.theme || 'system',
            default_page_size: data.appearance?.default_page_size || 20,
            motion_mode: normalizeMotionMode(data.appearance?.motion_mode)
          },
          tracking: {
            enabled: data.tracking?.enabled ?? true,
            ip_tracking: data.tracking?.ip_tracking ?? true,
            device_tracking: data.tracking?.device_tracking ?? true,
            location_tracking: data.tracking?.location_tracking ?? false
          }
        }
        applyMotionPreference(this.userSettings.appearance.motion_mode)
        return data
      } catch (error) {
        console.error('[Settings] 获取设置失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新用户设置
     * @param {Object} settings - 要更新的设置
     * @returns {Promise<void>}
     */
    async updateSettings(settings) {
      const { success, error: showError } = useMessage()
      try {
        const data = await updateUserSettings(settings)
        // 更新本地状态
        if (settings.profile) {
          this.userSettings.profile = {
            ...this.userSettings.profile,
            ...settings.profile
          }
        }
        if (settings.notifications) {
          this.userSettings.notifications = {
            ...this.userSettings.notifications,
            ...settings.notifications
          }
        }
        if (settings.appearance) {
          this.userSettings.appearance = {
            ...this.userSettings.appearance,
            ...settings.appearance,
            motion_mode: normalizeMotionMode(settings.appearance.motion_mode ?? this.userSettings.appearance.motion_mode)
          }
          applyMotionPreference(this.userSettings.appearance.motion_mode)
        }
        if (settings.tracking) {
          this.userSettings.tracking = {
            ...this.userSettings.tracking,
            ...settings.tracking
          }
        }
        success('设置保存成功')
        return data
      } catch (error) {
        showError('设置保存失败，请稍后重试')
        throw error
      }
    },

    /**
     * 修改密码
     * @param {string} oldPassword - 旧密码
     * @param {string} newPassword - 新密码
     * @returns {Promise<void>}
     */
    async changePassword(oldPassword, newPassword) {
      const { success, error: showError } = useMessage()
      try {
        await changePassword(oldPassword, newPassword)
        success('密码修改成功')
      } catch (error) {
        showError('密码修改失败，请检查旧密码是否正确')
        throw error
      }
    },

    /**
     * 获取登录设备列表
     * @returns {Promise<Array>}
     */
    async fetchDevices() {
      this.devicesLoading = true
      try {
        const data = await getLoginDevices()
        this.devices = data
        return data
      } catch (error) {
        console.error('[Settings] 获取设备列表失败:', error)
        throw error
      } finally {
        this.devicesLoading = false
      }
    },

    /**
     * 退出指定设备登录
     * @param {string} deviceId - 设备ID
     * @returns {Promise<void>}
     */
    async logoutDevice(deviceId) {
      const { success, error: showError } = useMessage()
      try {
        await logoutDeviceApi(deviceId)
        // 从本地列表中移除
        this.devices = this.devices.filter(d => d.id !== deviceId)
        success('已退出该设备登录')
      } catch (error) {
        showError('操作失败，请稍后重试')
        throw error
      }
    },

    /**
     * 退出所有设备登录
     * @returns {Promise<void>}
     */
    async logoutAllDevices() {
      const { success, error: showError } = useMessage()
      try {
        await logoutAllDevicesApi()
        this.devices = []
        success('已退出所有设备登录')
      } catch (error) {
        showError('操作失败，请稍后重试')
        throw error
      }
    },

    /**
     * 重置设置状态
     */
    $reset() {
      this.userSettings = {
        profile: {
          username: '',
          avatar: ''
        },
        notifications: {
          email: true,
          push: true
        },
        appearance: {
          theme: 'system',
          default_page_size: 20,
          motion_mode: 'system'
        },
        tracking: {
          enabled: true,
          ip_tracking: true,
          device_tracking: true,
          location_tracking: false
        }
      }
      this.devices = []
      this.loading = false
      this.devicesLoading = false
    }
  }
})
