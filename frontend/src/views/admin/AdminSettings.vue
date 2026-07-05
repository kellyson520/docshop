<template>
  <div class="settings-container motion-page motion-page--settings">
    <PageHeader
      title="系统设置"
      subtitle="管理个人资料、安全配置与跟踪偏好"
      :icon="Setting"
      :breadcrumbs="[
        { path: '/admin/dashboard', name: '首页' },
        { path: '/admin/settings', name: '设置' }
      ]"
    />

    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else>
      <el-card class="settings-card" shadow="hover">
        <el-tabs v-model="activeTab" class="settings-tabs" @tab-change="handleTabChange">
          <el-tab-pane label="个人信息" name="profile">
            <div class="tab-content">
              <h3 class="section-title">个人信息设置</h3>
              <el-form
                ref="profileFormRef"
                :model="profileForm"
                :rules="profileRules"
                label-width="100px"
                label-position="left"
                class="settings-form"
              >
                <el-form-item label="用户名" prop="username">
                  <el-input v-model="profileForm.username" placeholder="请输入用户名" maxlength="20" show-word-limit />
                </el-form-item>

                <el-form-item label="头像" prop="avatar">
                  <div class="avatar-upload">
                    <el-avatar :size="80" :src="profileForm.avatar || defaultAvatar" class="avatar-preview">
                      {{ profileForm.username?.charAt(0)?.toUpperCase() || 'U' }}
                    </el-avatar>
                    <div class="avatar-actions">
                      <el-upload
                        :show-file-list="false"
                        :before-upload="handleBeforeAvatarUpload"
                        :http-request="handleAvatarUpload"
                      >
                        <el-button size="small" :loading="avatarUploading" :disabled="avatarUploading">更换头像</el-button>
                      </el-upload>
                      <span class="upload-tip">支持 JPG、PNG，大小不超过 2MB</span>
                    </div>
                  </div>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" :loading="savingProfile" @click="handleSaveProfile">保存修改</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="通知设置" name="notifications">
            <div class="tab-content">
              <h3 class="section-title">通知设置</h3>
              <el-form label-width="100px" label-position="left" class="settings-form">
                <el-form-item label="邮件通知">
                  <el-switch
                    v-model="notificationForm.email"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleNotificationChange('email', notificationForm.email)"
                  />
                  <div class="form-tip">开启后，系统将通过邮件发送重要通知</div>
                </el-form-item>

                <el-form-item label="推送通知">
                  <el-switch
                    v-model="notificationForm.push"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleNotificationChange('push', notificationForm.push)"
                  />
                  <div class="form-tip">开启后，将接收浏览器推送通知</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="界面设置" name="appearance">
            <div class="tab-content">
              <h3 class="section-title">界面设置</h3>
              <el-form label-width="100px" label-position="left" class="settings-form">
                <el-form-item label="主题选择">
                  <el-radio-group v-model="appearanceForm.theme" @change="handleThemeChange">
                    <el-radio label="light">
                      <span class="radio-label"><el-icon><Sunny /></el-icon>亮色模式</span>
                    </el-radio>
                    <el-radio label="dark">
                      <span class="radio-label"><el-icon><Moon /></el-icon>暗色模式</span>
                    </el-radio>
                    <el-radio label="system">
                      <span class="radio-label"><el-icon><Monitor /></el-icon>跟随系统</span>
                    </el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="动效强度">
                  <el-select v-model="appearanceForm.motion_mode" class="motion-field" @change="handleMotionModeChange">
                    <el-option label="跟随系统" value="system" />
                    <el-option label="简化动效" value="reduced" />
                    <el-option label="关闭动效" value="off" />
                  </el-select>
                  <div class="form-tip">低配置设备可选择简化或关闭动效。</div>
                </el-form-item>

                <el-form-item label="每页条数">
                  <el-select v-model="appearanceForm.default_page_size" @change="handlePageSizeChange">
                    <el-option :value="10" label="10 条/页" />
                    <el-option :value="20" label="20 条/页" />
                    <el-option :value="50" label="50 条/页" />
                    <el-option :value="100" label="100 条/页" />
                  </el-select>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="安全设置" name="security">
            <div class="tab-content">
              <h3 class="section-title">修改密码</h3>
              <el-form
                ref="passwordFormRef"
                :model="passwordForm"
                :rules="passwordRules"
                label-width="120px"
                label-position="left"
                class="settings-form"
              >
                <el-form-item label="当前密码" prop="oldPassword">
                  <el-input v-model="passwordForm.oldPassword" type="password" placeholder="请输入当前密码" show-password />
                </el-form-item>
                <el-form-item label="新密码" prop="newPassword">
                  <el-input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码" show-password />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmPassword">
                  <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">修改密码</el-button>
                </el-form-item>
              </el-form>

              <el-divider />

              <h3 class="section-title">登录设备管理</h3>
              <div class="devices-section">
                <div class="devices-header">
                  <span class="devices-tip">当前登录设备列表，可退出不需要的设备。</span>
                  <el-button type="danger" text :loading="loggingOutAll" @click="handleLogoutAllDevices">退出所有设备</el-button>
                </div>

                <div v-if="devicesLoading" class="devices-loading">
                  <el-skeleton :rows="3" animated />
                </div>
                <div v-else-if="devices.length === 0" class="devices-empty">
                  <el-empty description="暂无登录设备记录" :image-size="60" />
                </div>
                <div v-else class="devices-list">
                  <div v-for="device in devices" :key="device.id" class="device-item">
                    <div class="device-icon"><el-icon><Monitor /></el-icon></div>
                    <div class="device-info">
                      <span class="device-name">{{ device.name || '未知设备' }}</span>
                      <span class="device-meta">
                        {{ device.browser || '未知浏览器' }} / {{ device.os || '未知系统' }}
                        <template v-if="device.last_active"> / {{ formatRelativeTime(device.last_active) }}</template>
                      </span>
                    </div>
                    <div class="device-actions">
                      <el-tag v-if="device.is_current" type="success" size="small">当前设备</el-tag>
                      <el-button
                        v-else
                        type="danger"
                        text
                        size="small"
                        :loading="loggingOutDevice === device.id"
                        @click="handleLogoutDevice(device.id)"
                      >
                        退出登录
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>

              <el-divider />

              <h3 class="section-title">系统安全配置</h3>
              <el-form label-width="140px" label-position="left" class="settings-form">
                <el-form-item label="强制 HTTPS">
                  <el-switch v-model="securityConfig.force_https" />
                  <span class="form-tip ml-2">无证书时请关闭，否则站点可能无法访问。</span>
                </el-form-item>

                <el-form-item label="CORS 允许域名">
                  <el-input
                    v-model="securityConfig.cors_origins_str"
                    type="textarea"
                    :rows="2"
                    placeholder="逗号分隔，例如: https://example.com, https://cdn.example.com"
                  />
                </el-form-item>

                <el-form-item label="请求限速">
                  <el-input-number v-model="securityConfig.rate_upload" :min="1" :max="1000" />
                  <span class="form-tip ml-2">次数 / 分钟 / 用户（全局 API 与上传统一生效）</span>
                </el-form-item>

                <el-form-item label="Token 过期">
                  <el-input-number v-model="securityConfig.token_expire" :min="5" :max="10080" />
                  <span class="form-tip ml-2">分钟（默认 1440 = 24h）</span>
                </el-form-item>

                <el-form-item label="最大文件大小">
                  <el-input-number v-model="securityConfig.max_file_mb" :min="1" :max="500" />
                  <span class="form-tip ml-2">MB</span>
                </el-form-item>

                <el-form-item label="日志级别">
                  <el-select v-model="securityConfig.log_level" placeholder="日志级别">
                    <el-option label="DEBUG" value="DEBUG" />
                    <el-option label="INFO" value="INFO" />
                    <el-option label="WARNING" value="WARNING" />
                    <el-option label="ERROR" value="ERROR" />
                  </el-select>
                </el-form-item>

                <el-form-item label="文件类型">
                  <el-input v-model="securityConfig.file_types_str" placeholder="逗号分隔，例如: .pdf,.docx,.xlsx" />
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" :loading="savingSecurity" @click="handleSaveSecurity">保存安全配置</el-button>
                  <el-button @click="loadSecurityConfig">重置</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="跟踪设置" name="tracking">
            <div class="tab-content">
              <h3 class="section-title">访问跟踪设置</h3>
              <el-form label-width="140px" label-position="left" class="settings-form">
                <el-form-item label="启用跟踪">
                  <el-switch
                    v-model="trackingForm.enabled"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('enabled', trackingForm.enabled)"
                  />
                </el-form-item>
                <el-form-item label="IP 跟踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.ip_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('ip_tracking', trackingForm.ip_tracking)"
                  />
                </el-form-item>
                <el-form-item label="设备跟踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.device_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('device_tracking', trackingForm.device_tracking)"
                  />
                </el-form-item>
                <el-form-item label="位置跟踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.location_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('location_tracking', trackingForm.location_tracking)"
                  />
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Sunny, Moon, Monitor } from '@element-plus/icons-vue'
import { uploadAvatar } from '@/api/settings'
import { get, put } from '@/api/client'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { createDependentRules, createRules, validateConfirmPassword, validatePassword, validateUsername } from '@/utils/validators'
import { applyMotionPreference, normalizeMotionMode } from '@/utils/motionPreference'
import { resolveAvatarUrl } from '@/utils/assetUrl'
import { useMessage } from '@/composables/useMessage'
import { useEventChannel } from '@/composables/useEventChannel'
import PageHeader from '@/components/common/PageHeader.vue'

defineOptions({ name: 'AdminSettings' })

const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const { success, error: showError } = useMessage()

const loading = ref(true)
const savingProfile = ref(false)
const avatarUploading = ref(false)
const changingPassword = ref(false)
const devicesLoading = ref(false)
const loggingOutAll = ref(false)
const loggingOutDevice = ref(null)
const savingSecurity = ref(false)

const defaultAvatar = ''
const activeTab = ref('profile')
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const devices = ref([])

const profileForm = reactive({
  username: '',
  avatar: '',
})

const notificationForm = reactive({
  email: true,
  push: true,
})

const appearanceForm = reactive({
  theme: 'system',
  default_page_size: 20,
  motion_mode: 'system',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const trackingForm = reactive({
  enabled: true,
  ip_tracking: true,
  device_tracking: true,
  location_tracking: false,
})

const securityConfig = reactive({
  force_https: false,
  cors_origins_str: '',
  rate_upload: 100,
  token_expire: 1440,
  max_file_mb: 50,
  log_level: 'INFO',
  file_types_str: '',
})

const profileRules = {
  username: createRules(validateUsername),
}

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: createRules(validatePassword),
  confirmPassword: createDependentRules(validateConfirmPassword, () => passwordForm.newPassword),
}

function parseCommaList(value) {
  if (Array.isArray(value)) return value
  return String(value || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

async function loadSecurityConfig(options = {}) {
  const { silent = false } = options
  try {
    const data = await get('/settings')
    if (!data) return
    securityConfig.force_https = data.force_https ?? false
    securityConfig.cors_origins_str = Array.isArray(data.cors_origins) ? data.cors_origins.join(', ') : (data.cors_origins || '')
    securityConfig.rate_upload = data.rate_upload ?? 100
    securityConfig.token_expire = data.token_expire ?? 1440
    securityConfig.max_file_mb = data.max_file_mb ?? (data.max_file_size || 52428800) / (1024 * 1024)
    securityConfig.log_level = data.log_level ?? 'INFO'
    securityConfig.file_types_str = Array.isArray(data.file_types) ? data.file_types.join(', ') : (data.file_types || '')
  } catch (error) {
    console.error('[Settings] load security config failed:', error)
    if (!silent) ElMessage.error('Failed to load security settings')
  }
}

async function handleSaveSecurity() {
  savingSecurity.value = true
  try {
    await put('/settings', {
      force_https: securityConfig.force_https,
      cors_origins: parseCommaList(securityConfig.cors_origins_str),
      rate_upload: securityConfig.rate_upload,
      token_expire: securityConfig.token_expire,
      max_file_mb: securityConfig.max_file_mb,
      log_level: securityConfig.log_level,
      file_types: parseCommaList(securityConfig.file_types_str),
    })
    await loadSecurityConfig({ silent: true })
    ElMessage.success('运行期配置已写入 .env 并立即生效')
  } catch (err) {
    ElMessage.error(`Save failed: ${err.message || ''}`)
  } finally {
    savingSecurity.value = false
  }
}

async function loadSettings() {
  loading.value = true
  try {
    await settingsStore.fetchSettings()
    profileForm.username = settingsStore.userSettings.profile?.username || ''
    profileForm.avatar = resolveAvatarUrl(settingsStore.userSettings.profile?.avatar || '')
    notificationForm.email = settingsStore.userSettings.notifications?.email ?? true
    notificationForm.push = settingsStore.userSettings.notifications?.push ?? true
    appearanceForm.theme = settingsStore.userSettings.appearance?.theme || 'system'
    appearanceForm.default_page_size = settingsStore.userSettings.appearance?.default_page_size || 20
    appearanceForm.motion_mode = normalizeMotionMode(settingsStore.userSettings.appearance?.motion_mode)
    trackingForm.enabled = settingsStore.userSettings.tracking?.enabled ?? true
    trackingForm.ip_tracking = settingsStore.userSettings.tracking?.ip_tracking ?? true
    trackingForm.device_tracking = settingsStore.userSettings.tracking?.device_tracking ?? true
    trackingForm.location_tracking = settingsStore.userSettings.tracking?.location_tracking ?? false
  } catch (error) {
    console.error('[Settings] 加载设置失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  if (activeTab.value !== 'security') return
  devicesLoading.value = true
  try {
    devices.value = await settingsStore.fetchDevices()
  } catch (error) {
    console.error('[Settings] 加载设备列表失败:', error)
  } finally {
    devicesLoading.value = false
  }
}

async function handleSaveProfile() {
  if (profileFormRef.value?.validate) {
    try {
      await profileFormRef.value.validate()
    } catch {
      return
    }
  }

  savingProfile.value = true
  try {
    await settingsStore.updateSettings({
      profile: {
        username: profileForm.username,
        avatar: profileForm.avatar,
      },
    })
    if (authStore.user) {
      authStore.user = {
        ...authStore.user,
        username: profileForm.username,
        avatar: profileForm.avatar,
      }
    }
    success('Profile saved')
  } catch (error) {
    showError(error.message || 'Failed to save profile, please retry')
  } finally {
    savingProfile.value = false
  }
}

function handleBeforeAvatarUpload(file) {
  const isImage = ['image/jpeg', 'image/png'].includes(file.type)
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) {
    ElMessage.error('只能上传 JPG 或 PNG 格式的图片')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

async function handleAvatarUpload({ file }) {
  avatarUploading.value = true
  try {
    const data = await uploadAvatar(file)
    const avatarUrl = resolveAvatarUrl(data.avatar_url || data.url)
    if (!avatarUrl) throw new Error('Avatar URL missing')
    profileForm.avatar = avatarUrl
    settingsStore.userSettings.profile.avatar = avatarUrl
    if (authStore.user) authStore.user.avatar = avatarUrl
    success('头像上传成功')
  } catch {
    showError('头像上传失败，请重试')
  } finally {
    avatarUploading.value = false
  }
}

async function handleNotificationChange(key, value) {
  try {
    await settingsStore.updateSettings({ notifications: { [key]: value } })
  } catch {
    notificationForm[key] = !value
  }
}

async function handleThemeChange(theme) {
  try {
    await settingsStore.updateSettings({ appearance: { theme } })
    document.documentElement.setAttribute('data-theme', theme === 'system' ? '' : theme)
  } catch {
    appearanceForm.theme = settingsStore.userSettings.appearance?.theme || 'system'
  }
}

async function handlePageSizeChange(size) {
  try {
    await settingsStore.updateSettings({ appearance: { default_page_size: size } })
  } catch {
    appearanceForm.default_page_size = settingsStore.userSettings.appearance?.default_page_size || 20
  }
}

async function handleMotionModeChange(mode) {
  const nextMode = normalizeMotionMode(mode)
  applyMotionPreference(nextMode)
  try {
    await settingsStore.updateSettings({ appearance: { motion_mode: nextMode } })
  } catch {
    appearanceForm.motion_mode = normalizeMotionMode(settingsStore.userSettings.appearance?.motion_mode)
    applyMotionPreference(appearanceForm.motion_mode)
  }
}

async function handleChangePassword() {
  if (passwordFormRef.value?.validate) {
    try {
      await passwordFormRef.value.validate()
    } catch {
      return
    }
  }

  changingPassword.value = true
  try {
    await settingsStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordFormRef.value?.resetFields?.()
    success('Password changed')
  } catch (error) {
    showError(error.message || 'Failed to change password, please retry')
  } finally {
    changingPassword.value = false
  }
}

async function handleTrackingChange(key, value) {
  if (key === 'enabled' && !value) {
    trackingForm.ip_tracking = false
    trackingForm.device_tracking = false
    trackingForm.location_tracking = false
  }

  try {
    await settingsStore.updateSettings({
      tracking: {
        enabled: trackingForm.enabled,
        ip_tracking: trackingForm.ip_tracking,
        device_tracking: trackingForm.device_tracking,
        location_tracking: trackingForm.location_tracking,
      },
    })
  } catch {
    await loadSettings()
  }
}

async function handleLogoutDevice(deviceId) {
  loggingOutDevice.value = deviceId
  try {
    await settingsStore.logoutDevice(deviceId)
    devices.value = devices.value.filter(device => device.id !== deviceId)
  } finally {
    loggingOutDevice.value = null
  }
}

async function handleLogoutAllDevices() {
  loggingOutAll.value = true
  try {
    await settingsStore.logoutAllDevices()
    devices.value = []
  } catch {
    // noop
  } finally {
    loggingOutAll.value = false
  }
}

function formatRelativeTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  return `${Math.floor(diff / day)} 天前`
}

function handleTabChange(tab) {
  activeTab.value = tab
  if (tab === 'security') {
    void loadDevices()
    void loadSecurityConfig()
  }
}

useEventChannel({
  topics: ['config'],
  onEvent: (event) => {
    if (event?.data?.topic === 'config' && event?.data?.type === 'config.updated') {
      void loadSecurityConfig({ silent: true })
    }
  },
})

onMounted(() => {
  void loadSettings()
})
</script>

<style scoped>
.settings-container {
  max-width: 900px;
  margin: 0 auto;
}

.loading-wrapper {
  padding: 20px;
}

.settings-card {
  min-height: 500px;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
}

.tab-content {
  max-width: 600px;
}

.section-title {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.settings-form {
  padding: 0 10px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.avatar-upload {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-preview {
  border: 2px dashed #dcdfe6;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.devices-section {
  margin-top: 16px;
}

.devices-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.devices-tip {
  font-size: 14px;
  color: #909399;
}

.devices-loading,
.devices-empty {
  padding: 20px 0;
}

.devices-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.device-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.device-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: var(--surface-panel, #fff);
  border-radius: 8px;
  color: var(--workspace-blue, #2f5d8c);
  font-size: 20px;
}

.device-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.device-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #172033);
}

.device-meta {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
}

.device-actions {
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .tab-content {
    max-width: 100%;
  }

  .settings-form {
    padding: 0;
  }

  .settings-form :deep(.el-form-item) {
    display: block !important;
  }

  .settings-form :deep(.el-form-item__label) {
    width: 100% !important;
    justify-content: flex-start !important;
    margin-bottom: 8px !important;
    padding: 0 !important;
  }

  .settings-form :deep(.el-form-item__content) {
    width: 100%;
    margin-left: 0 !important;
  }

  .avatar-upload {
    flex-direction: column;
    align-items: center;
    gap: 16px;
    text-align: center;
  }

  .avatar-actions {
    align-items: center;
    width: 100%;
  }

  .devices-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .device-item {
    flex-wrap: wrap;
  }

  .device-info {
    flex-basis: calc(100% - 52px);
  }

  .device-actions {
    width: 100%;
    justify-content: flex-end;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #e4e7ed;
  }
}
</style>
