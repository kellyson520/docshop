<!--
  系统设置页面
  包含个人信息、通知、界面、安全和追踪等设置
-->
<template>
  <div class="settings-container">
    <!-- 页面头部 -->
    <PageHeader
      title="系统设置"
      subtitle="管理您的个人设置和偏好"
      :icon="Setting"
      :breadcrumbs="[
        { path: '/admin/dashboard', name: '首页' },
        { path: '/admin/settings', name: '设置' }
      ]"
    />

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else>
      <!-- 设置标签页 -->
      <el-card class="settings-card" shadow="hover">
        <el-tabs v-model="activeTab" class="settings-tabs">
          <!-- 个人信息 -->
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
                  <el-input
                    v-model="profileForm.username"
                    placeholder="请输入用户名"
                    maxlength="20"
                    show-word-limit
                  />
                </el-form-item>

                <el-form-item label="头像" prop="avatar">
                  <div class="avatar-upload">
                    <el-avatar
                      :size="80"
                      :src="profileForm.avatar || defaultAvatar"
                      class="avatar-preview"
                    >
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
                      <span class="upload-tip">支持 JPG、PNG 格式，大小不超过 2MB</span>
                    </div>
                  </div>
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="savingProfile"
                    @click="handleSaveProfile"
                  >
                    保存修改
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 通知设置 -->
          <el-tab-pane label="通知设置" name="notifications">
            <div class="tab-content">
              <h3 class="section-title">通知设置</h3>
              <el-form
                label-width="100px"
                label-position="left"
                class="settings-form"
              >
                <el-form-item label="邮件通知">
                  <el-switch
                    v-model="notificationForm.email"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleNotificationChange('email', notificationForm.email)"
                  />
                  <div class="form-tip">开启后，系统将通过邮件向您发送重要通知</div>
                </el-form-item>

                <el-form-item label="推送通知">
                  <el-switch
                    v-model="notificationForm.push"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleNotificationChange('push', notificationForm.push)"
                  />
                  <div class="form-tip">开启后，将收到浏览器推送通知</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 界面设置 -->
          <el-tab-pane label="界面设置" name="appearance">
            <div class="tab-content">
              <h3 class="section-title">界面设置</h3>
              <el-form
                label-width="100px"
                label-position="left"
                class="settings-form"
              >
                <el-form-item label="主题选择">
                  <el-radio-group v-model="appearanceForm.theme" @change="handleThemeChange">
                    <el-radio label="light">
                      <span class="radio-label">
                        <el-icon><Sunny /></el-icon>
                        亮色模式
                      </span>
                    </el-radio>
                    <el-radio label="dark">
                      <span class="radio-label">
                        <el-icon><Moon /></el-icon>
                        暗色模式
                      </span>
                    </el-radio>
                    <el-radio label="system">
                      <span class="radio-label">
                        <el-icon><Monitor /></el-icon>
                        跟随系统
                      </span>
                    </el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="每页条数">
                  <el-select v-model="appearanceForm.default_page_size" @change="handlePageSizeChange">
                    <el-option :value="10" label="10 条/页" />
                    <el-option :value="20" label="20 条/页" />
                    <el-option :value="50" label="50 条/页" />
                    <el-option :value="100" label="100 条/页" />
                  </el-select>
                  <div class="form-tip">设置列表默认每页显示的条目数量</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 安全设置 -->
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
                  <el-input
                    v-model="passwordForm.oldPassword"
                    type="password"
                    placeholder="请输入当前密码"
                    show-password
                  />
                </el-form-item>

                <el-form-item label="新密码" prop="newPassword">
                  <el-input
                    v-model="passwordForm.newPassword"
                    type="password"
                    placeholder="请输入新密码（至少6位）"
                    show-password
                  />
                </el-form-item>

                <el-form-item label="确认密码" prop="confirmPassword">
                  <el-input
                    v-model="passwordForm.confirmPassword"
                    type="password"
                    placeholder="请再次输入新密码"
                    show-password
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="changingPassword"
                    @click="handleChangePassword"
                  >
                    修改密码
                  </el-button>
                </el-form-item>
              </el-form>

              <el-divider />

              <h3 class="section-title">登录设备管理</h3>
              <div class="devices-section">
                <div class="devices-header">
                  <span class="devices-tip">当前登录的设备列表，您可以退出不需要的设备</span>
                  <el-button
                    type="danger"
                    text
                    :loading="loggingOutAll"
                    @click="handleLogoutAllDevices"
                  >
                    退出所有设备
                  </el-button>
                </div>

                <div v-if="devicesLoading" class="devices-loading">
                  <el-skeleton :rows="3" animated />
                </div>

                <div v-else-if="devices.length === 0" class="devices-empty">
                  <el-empty description="暂无登录设备记录" :image-size="60" />
                </div>

                <div v-else class="devices-list">
                  <div
                    v-for="device in devices"
                    :key="device.id"
                    class="device-item"
                  >
                    <div class="device-icon">
                      <el-icon><Monitor /></el-icon>
                    </div>
                    <div class="device-info">
                      <span class="device-name">{{ device.name || '未知设备' }}</span>
                      <span class="device-meta">
                        {{ device.browser || '未知浏览器' }} · {{ device.os || '未知系统' }}
                        <template v-if="device.last_active"> · {{ formatRelativeTime(device.last_active) }}</template>
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
            </div>

            <el-divider />

            <h3 class="section-title">系统安全配置</h3>
            <el-form label-width="140px" label-position="left" class="settings-form">
              <el-form-item label="强制 HTTPS">
                <el-switch v-model="securityConfig.force_https" />
                <span class="form-tip ml-2">无证书时请关闭，否则网站无法访问</span>
              </el-form-item>

              <el-form-item label="CORS 允许域名">
                <el-input
                  v-model="securityConfig.cors_origins_str"
                  type="textarea"
                  :rows="2"
                  placeholder="逗号分隔，如: https://example.com, https://cdn.example.com"
                />
              </el-form-item>

              <el-form-item label="上传限速">
                <el-input-number v-model="securityConfig.rate_upload" :min="1" :max="1000" />
                <span class="form-tip ml-2">次 / 分钟 / 用户</span>
              </el-form-item>

              <el-form-item label="API 限速">
                <el-input-number v-model="securityConfig.rate_api" :min="1" :max="10000" />
                <span class="form-tip ml-2">次 / 分钟 / 用户</span>
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
                <el-input
                  v-model="securityConfig.file_types_str"
                  placeholder="逗号分隔，如: .pdf,.docx,.xlsx"
                /></el-form-item>

              <el-form-item>
                <el-button type="primary" :loading="savingSecurity" @click="handleSaveSecurity">
                  保存安全配置
                </el-button>
                <el-button @click="loadSecurityConfig">重置</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 追踪设置 -->
          <el-tab-pane label="追踪设置" name="tracking">
            <div class="tab-content">
              <h3 class="section-title">访问追踪设置</h3>
              <el-form
                label-width="140px"
                label-position="left"
                class="settings-form"
              >
                <el-form-item label="启用追踪">
                  <el-switch
                    v-model="trackingForm.enabled"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('enabled', trackingForm.enabled)"
                  />
                  <div class="form-tip">开启后，系统将记录您的访问行为用于数据分析</div>
                </el-form-item>

                <el-form-item label="IP追踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.ip_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('ip_tracking', trackingForm.ip_tracking)"
                  />
                  <div class="form-tip">记录访问者的 IP 地址</div>
                </el-form-item>

                <el-form-item label="设备追踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.device_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('device_tracking', trackingForm.device_tracking)"
                  />
                  <div class="form-tip">记录访问者使用的浏览器和操作系统</div>
                </el-form-item>

                <el-form-item label="位置追踪" :disabled="!trackingForm.enabled">
                  <el-switch
                    v-model="trackingForm.location_tracking"
                    active-text="开启"
                    inactive-text="关闭"
                    @change="handleTrackingChange('location_tracking', trackingForm.location_tracking)"
                  />
                  <div class="form-tip">通过 IP 地址推算访问者的大致地理位置</div>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Setting,
  Sunny,
  Moon,
  Monitor
} from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { validateUsername, validatePassword } from '@/utils/validators'
import { createRules, createDependentRules, validateConfirmPassword } from '@/utils/validators'
import { useMessage } from '@/composables/useMessage'
import PageHeader from '@/components/common/PageHeader.vue'
import { uploadAvatar } from '@/api/settings'
import { get, put } from '@/api/client'

defineOptions({ name: 'AdminSettings' })

const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const { success, error: showError } = useMessage()

// 加载状态
const loading = ref(true)
const savingProfile = ref(false)
const avatarUploading = ref(false)
const changingPassword = ref(false)
const devicesLoading = ref(false)
const loggingOutAll = ref(false)
const loggingOutDevice = ref(null)

// 默认头像
const defaultAvatar = ''

// 当前激活的标签页
const activeTab = ref('profile')

// 表单引用
const profileFormRef = ref(null)
const passwordFormRef = ref(null)

// 个人信息表单
const profileForm = reactive({
  username: '',
  avatar: ''
})

// 通知设置表单
const notificationForm = reactive({
  email: true,
  push: true
})

// 界面设置表单
const appearanceForm = reactive({
  theme: 'system',
  default_page_size: 20
})

// 密码表单
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 追踪设置表单
const trackingForm = reactive({
  enabled: true,
  ip_tracking: true,
  device_tracking: true,
  location_tracking: false
})

// 登录设备列表
const devices = ref([])

// 系统安全配置
const savingSecurity = ref(false)
const securityConfig = reactive({
  force_https: false,
  cors_origins_str: '',
  rate_upload: 100,
  token_expire: 1440,
  max_file_mb: 50,
  log_level: 'INFO',
  file_types_str: '',
})

async function loadSecurityConfig() {
  try {
    const data = await get('/settings')
    if (data) {
      securityConfig.force_https = data.force_https ?? false
      securityConfig.cors_origins_str = Array.isArray(data.cors_origins) ? data.cors_origins.join(', ') : (data.cors_origins || '')
      securityConfig.rate_upload = data.rate_upload ?? 100
      securityConfig.token_expire = data.token_expire ?? 1440
      securityConfig.max_file_mb = data.max_file_mb ?? (data.max_file_size || 52428800) / (1024 * 1024)
      securityConfig.log_level = data.log_level ?? 'INFO'
      securityConfig.file_types_str = Array.isArray(data.file_types) ? data.file_types.join(', ') : (data.file_types || '')
    }
  } catch { /* ignore */ }
}

async function handleSaveSecurity() {
  savingSecurity.value = true
  try {
    await put('/settings', {
      cors_origins_str: securityConfig.cors_origins_str,
      rate_upload: securityConfig.rate_upload,
      token_expire: securityConfig.token_expire,
      max_file_mb: securityConfig.max_file_mb,
      log_level: securityConfig.log_level,
      file_types: securityConfig.file_types_str,
    })
    ElMessage.success('配置已保存到 .env')
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.message || ''))
  } finally {
    savingSecurity.value = false
  }
}

// 表单校验规则
const profileRules = {
  username: createRules(validateUsername)
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: createRules(validatePassword),
  confirmPassword: createDependentRules(validateConfirmPassword, () => passwordForm.newPassword)
}

/**
 * 加载设置数据
 */
async function loadSettings() {
  loading.value = true
  try {
    await settingsStore.fetchSettings()

    // 填充表单数据
    profileForm.username = settingsStore.userSettings.profile?.username || ''
    profileForm.avatar = settingsStore.userSettings.profile?.avatar || ''

    notificationForm.email = settingsStore.userSettings.notifications?.email ?? true
    notificationForm.push = settingsStore.userSettings.notifications?.push ?? true

    appearanceForm.theme = settingsStore.userSettings.appearance?.theme || 'system'
    appearanceForm.default_page_size = settingsStore.userSettings.appearance?.default_page_size || 20

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

/**
 * 加载登录设备列表
 */
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

/**
 * 保存个人信息
 */
async function handleSaveProfile() {
  if (!profileFormRef.value) return

  try {
    await profileFormRef.value.validate()
  } catch {
    return
  }

  savingProfile.value = true
  try {
    await settingsStore.updateSettings({
      profile: {
        username: profileForm.username,
        avatar: profileForm.avatar
      }
    })
    if (authStore.user) {
      authStore.user = {
        ...authStore.user,
        username: profileForm.username,
        avatar: profileForm.avatar
      }
    }
  } finally {
    savingProfile.value = false
  }
}

/**
 * 头像上传前校验
 */
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

/**
 * 上传头像
 */
async function handleAvatarUpload({ file }) {
  avatarUploading.value = true
  try {
    const data = await uploadAvatar(file)
    const avatarUrl = data.avatar_url || data.url
    if (!avatarUrl) {
      throw new Error('Avatar URL missing')
    }
    profileForm.avatar = avatarUrl
    settingsStore.userSettings.profile.avatar = avatarUrl
    if (authStore.user) {
      authStore.user.avatar = avatarUrl
    }
    success('头像上传成功')
  } catch (error) {
    showError('头像上传失败，请重试')
  } finally {
    avatarUploading.value = false
  }
}

/**
 * 通知设置变更
 */
async function handleNotificationChange(key, value) {
  try {
    await settingsStore.updateSettings({
      notifications: { [key]: value }
    })
  } catch (error) {
    // 回滚 UI 状态
    notificationForm[key] = !value
  }
}

/**
 * 主题变更
 */
async function handleThemeChange(theme) {
  try {
    await settingsStore.updateSettings({
      appearance: { theme }
    })
    // 可以在这里触发全局主题变更事件
    document.documentElement.setAttribute('data-theme', theme === 'system' ? '' : theme)
  } catch (error) {
    appearanceForm.theme = settingsStore.userSettings.appearance?.theme || 'system'
  }
}

/**
 * 每页条数变更
 */
async function handlePageSizeChange(size) {
  try {
    await settingsStore.updateSettings({
      appearance: { default_page_size: size }
    })
  } catch (error) {
    appearanceForm.default_page_size = settingsStore.userSettings.appearance?.default_page_size || 20
  }
}

/**
 * 修改密码
 */
async function handleChangePassword() {
  if (!passwordFormRef.value) return

  try {
    await passwordFormRef.value.validate()
  } catch {
    return
  }

  changingPassword.value = true
  try {
    await settingsStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    // 清空表单
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordFormRef.value?.resetFields()
  } finally {
    changingPassword.value = false
  }
}

/**
 * 追踪设置变更
 */
async function handleTrackingChange(key, value) {
  // 如果禁用追踪，同时禁用其他追踪选项
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
        location_tracking: trackingForm.location_tracking
      }
    })
  } catch (error) {
    // 回滚 UI 状态
    await loadSettings()
  }
}

/**
 * 退出指定设备
 */
async function handleLogoutDevice(deviceId) {
  loggingOutDevice.value = deviceId
  try {
    await settingsStore.logoutDevice(deviceId)
    devices.value = devices.value.filter(d => d.id !== deviceId)
  } finally {
    loggingOutDevice.value = null
  }
}

/**
 * 退出所有设备
 */
async function handleLogoutAllDevices() {
  try {
    await settingsStore.logoutAllDevices()
    devices.value = []
  } catch (error) {
    // 忽略错误
  }
}

/**
 * 格式化相对时间
 */
function formatRelativeTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)} 分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} 小时前`
  } else {
    return `${Math.floor(diff / day)} 天前`
  }
}

// 监听标签页切换，加载设备列表
function handleTabChange(tab) {
  if (tab === 'security') {
    loadDevices()
    loadSecurityConfig()
  }
}

onMounted(() => {
  loadSettings()
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

/* 头像上传 */
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

/* 主题选择 */
.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 设备管理 */
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

.devices-loading {
  padding: 20px 0;
}

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
  transition: background-color 0.2s;
}

.device-item:hover {
  background-color: #ecf5ff;
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

/* 响应式适配 */
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

  .upload-tip {
    max-width: 100%;
    line-height: 1.6;
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
