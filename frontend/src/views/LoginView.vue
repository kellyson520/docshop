<template>
  <div class="login-container motion-page motion-page--login">
    <div class="login-box">
      <!-- 返回首页 -->
      <div class="back-home">
        <router-link to="/" class="back-link">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </router-link>
      </div>

      <!-- Logo 区域 -->
      <div class="login-header">
        <div class="logo-wrapper" @click="$router.push('/')">
          <el-icon :size="56" color="#667eea"><DocumentChecked /></el-icon>
        </div>
        <h1 class="login-title">DocShop</h1>
        <p class="login-subtitle">智能文档版本管理系统</p>
      </div>

      <!-- 登录表单 -->
      <el-card shadow="hover" class="login-card">
        <el-tabs v-model="activeTab" stretch class="login-tabs">
          <!-- 登录标签页 -->
          <el-tab-pane label="账号登录" name="login">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              status-icon
              class="login-form"
              @keyup.enter="handleLogin"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  :prefix-icon="User"
                  clearable
                  size="large"
                  class="login-input"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  :type="passwordVisible ? 'text' : 'password'"
                  placeholder="请输入密码"
                  :prefix-icon="Lock"
                  size="large"
                  class="login-input"
                >
                  <template #suffix>
                    <el-icon
                      class="password-toggle"
                      @click="passwordVisible = !passwordVisible"
                    >
                      <View v-if="passwordVisible" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <div class="login-options">
                <el-checkbox v-model="rememberUsername">记住用户名</el-checkbox>
                <el-button link type="primary" class="forgot-link" @click="handleForgotPassword">
                  忘记密码？
                </el-button>
              </div>

              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  class="login-button"
                  :loading="loading"
                  @click="handleLogin"
                >
                  {{ loading ? '登录中...' : '立即登录' }}
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 社交登录 -->
            <div class="social-login">
              <div class="divider">
                <span>其他登录方式</span>
              </div>
              <div class="social-icons">
                <el-tooltip content="微信登录" placement="top">
                  <div class="social-icon wechat">
                    <el-icon :size="20"><ChatDotRound /></el-icon>
                  </div>
                </el-tooltip>
                <el-tooltip content="QQ登录" placement="top">
                  <div class="social-icon qq">
                    <el-icon :size="20"><ChatLineRound /></el-icon>
                  </div>
                </el-tooltip>
                <el-tooltip content="企业微信登录" placement="top">
                  <div class="social-icon workwechat">
                    <el-icon :size="20"><OfficeBuilding /></el-icon>
                  </div>
                </el-tooltip>
              </div>
            </div>
          </el-tab-pane>

          <!-- 注册标签页 -->
          <el-tab-pane v-if="registrationPolicy.can_register" label="注册账号" name="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              status-icon
              class="login-form"
              @keyup.enter="handleRegister"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名"
                  :prefix-icon="User"
                  clearable
                  size="large"
                  class="login-input"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  :type="regPasswordVisible ? 'text' : 'password'"
                  placeholder="请输入密码（至少6位）"
                  :prefix-icon="Lock"
                  size="large"
                  class="login-input"
                >
                  <template #suffix>
                    <el-icon
                      class="password-toggle"
                      @click="regPasswordVisible = !regPasswordVisible"
                    >
                      <View v-if="regPasswordVisible" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  :type="regPasswordVisible ? 'text' : 'password'"
                  placeholder="请确认密码"
                  :prefix-icon="Lock"
                  size="large"
                  class="login-input"
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  class="login-button"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  {{ registerLoading ? '注册中...' : '立即注册' }}
                </el-button>
              </el-form-item>
            </el-form>

            <div class="register-agreement">
              <el-checkbox v-model="agreeTerms">
                我已阅读并同意
                <el-button link type="primary" @click="showTerms">服务条款</el-button>
                和
                <el-button link type="primary" @click="showPrivacy">隐私政策</el-button>
              </el-checkbox>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- 页脚 -->
      <div class="login-footer">
        <p>&copy; 2024 DocShop. All rights reserved.</p>
        <div class="footer-links">
          <router-link to="/">关于我们</router-link>
          <span class="divider">|</span>
          <router-link to="/">帮助中心</router-link>
          <span class="divider">|</span>
          <router-link to="/">联系我们</router-link>
        </div>
      </div>
    </div>

    <!-- 过期提示 -->
    <el-alert
      v-if="isExpired"
      title="登录已过期，请重新登录"
      type="warning"
      show-icon
      :closable="false"
      class="expired-alert"
    />

    <!-- 忘记密码对话框 -->
    <el-dialog v-model="forgotDialogVisible" title="找回密码" width="400px" destroy-on-close>
      <el-steps :active="forgotStep" finish-status="success" simple class="forgot-steps">
        <el-step title="验证身份" />
        <el-step title="重置密码" />
        <el-step title="完成" />
      </el-steps>
      
      <div v-if="forgotStep === 0" class="forgot-content">
        <p class="forgot-tip">请输入您的用户名或绑定的邮箱</p>
        <el-input v-model="forgotForm.account" placeholder="用户名/邮箱" size="large" class="forgot-input">
          <template #prefix>
            <el-icon><User /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" size="large" class="forgot-btn" @click="sendResetCode">
          发送验证码
        </el-button>
      </div>
      
      <div v-if="forgotStep === 1" class="forgot-content">
        <p class="forgot-tip">请输入验证码和新密码</p>
        <el-input v-model="forgotForm.code" placeholder="验证码" size="large" class="forgot-input">
          <template #prefix>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
        <el-input v-model="forgotForm.newPassword" type="password" placeholder="新密码" size="large" class="forgot-input" show-password>
          <template #prefix>
            <el-icon><Lock /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" size="large" class="forgot-btn" @click="resetPassword">
          重置密码
        </el-button>
      </div>
      
      <div v-if="forgotStep === 2" class="forgot-content forgot-success">
        <el-icon :size="64" color="#67c23a"><CircleCheck /></el-icon>
        <p class="success-text">密码重置成功！</p>
        <p class="success-tip">请使用新密码登录</p>
        <el-button type="primary" size="large" @click="forgotDialogVisible = false; activeTab = 'login'">
          去登录
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  User, Lock, View, Hide, DocumentChecked, ArrowLeft,
  ChatDotRound, ChatLineRound, OfficeBuilding, Key, CircleCheck
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getRegistrationPolicy } from '@/api/auth'
import { useLoading } from '@/composables/useLoading'
import { 
  validateUsername, 
  validatePassword, 
  validateConfirmPassword,
  createRules,
  createDependentRules
} from '@/utils/validators'
import { ErrorHandler } from '@/utils/error'

// ==================== 路由和状态 ====================
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// ==================== 响应式数据 ====================
const activeTab = ref('login')
const passwordVisible = ref(false)
const regPasswordVisible = ref(false)
const rememberUsername = ref(false)
const isExpired = ref(false)
const agreeTerms = ref(false)
const registrationPolicy = ref({ enabled: false, first_user: false, can_register: false })

// 登录表单
const loginFormRef = ref(null)
const loginForm = ref({
  username: '',
  password: ''
})

// 注册表单
const registerFormRef = ref(null)
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

// 忘记密码
const forgotDialogVisible = ref(false)
const forgotStep = ref(0)
const forgotForm = ref({
  account: '',
  code: '',
  newPassword: ''
})

// 加载状态
const { loading, start: startLoading, stop: stopLoading } = useLoading()
const { 
  loading: registerLoading, 
  start: startRegisterLoading, 
  stop: stopRegisterLoading 
} = useLoading()

// ==================== 表单校验规则 ====================
const loginRules = {
  username: createRules(validateUsername),
  password: createRules(validatePassword)
}

const registerRules = {
  username: createRules(validateUsername),
  password: createRules(validatePassword),
  confirmPassword: createDependentRules(
    validateConfirmPassword,
    () => registerForm.value.password
  )
}

// ==================== 生命周期 ====================
onMounted(async () => {
  // 检查是否过期跳转
  isExpired.value = route.query.expired === '1'
  
  // 读取记住的用户名
  const savedUsername = localStorage.getItem('remembered_username')
  if (savedUsername) {
    loginForm.value.username = savedUsername
    rememberUsername.value = true
  }
  
  // 如果已登录，跳转到首页
  if (authStore.isLoggedIn) {
    router.replace('/admin')
  }

  await fetchRegistrationPolicy()
})

// ==================== 方法 ====================

/**
 * 处理登录
 */
async function fetchRegistrationPolicy() {
  try {
    registrationPolicy.value = await getRegistrationPolicy()
    if (!registrationPolicy.value.can_register && activeTab.value === 'register') {
      activeTab.value = 'login'
    }
  } catch {
    registrationPolicy.value = { enabled: false, first_user: false, can_register: false }
    if (activeTab.value === 'register') activeTab.value = 'login'
  }
}

async function handleLogin() {
  if (!loginFormRef.value) return
  
  try {
    // 表单校验
    await loginFormRef.value.validate()
  } catch {
    return
  }
  
  startLoading('登录中...')
  
  try {
    // 执行登录
    await authStore.login(loginForm.value.username, loginForm.value.password)
    
    // 记住用户名
    if (rememberUsername.value) {
      localStorage.setItem('remembered_username', loginForm.value.username)
    } else {
      localStorage.removeItem('remembered_username')
    }
    
    ElMessage.success('登录成功')
    
    // 跳转到原页面或首页（白名单防开放重定向）
    const raw = route.query.redirect
    const safe = typeof raw === 'string' && raw.startsWith('/') && !raw.startsWith('//')
    const redirect = safe ? raw : '/admin'
    router.replace(redirect)
  } catch (error) {
    // 使用错误处理器处理错误
    ErrorHandler.handle(error, { 
      fallbackMessage: '登录失败，请检查用户名和密码'
    })
  } finally {
    stopLoading()
  }
}

/**
 * 处理注册
 */
async function handleRegister() {
  if (!registerFormRef.value) return
  
  if (!agreeTerms.value) {
    ElMessage.warning('请先同意服务条款和隐私政策')
    return
  }
  
  try {
    // 表单校验
    await registerFormRef.value.validate()
  } catch {
    return
  }
  
  startRegisterLoading('注册中...')
  
  try {
    // 导入注册 API
    const { register } = await import('@/api/auth')
    await register(registerForm.value.username, registerForm.value.password)
    
    ElMessage.success('注册成功，请登录')
    
    // 切换到登录页并填充用户名
    activeTab.value = 'login'
    loginForm.value.username = registerForm.value.username
    loginForm.value.password = ''
    
    // 清空注册表单
    registerForm.value = {
      username: '',
      password: '',
      confirmPassword: ''
    }
    agreeTerms.value = false
  } catch (error) {
    ErrorHandler.handle(error, {
      fallbackMessage: '注册失败，请稍后重试'
    })
  } finally {
    stopRegisterLoading()
  }
}

/**
 * 处理忘记密码
 */
function handleForgotPassword() {
  forgotDialogVisible.value = true
  forgotStep.value = 0
  forgotForm.value = { account: '', code: '', newPassword: '' }
}

function sendResetCode() {
  if (!forgotForm.value.account) {
    ElMessage.warning('请输入用户名或邮箱')
    return
  }
  // 密码重置功能正在开发中
  ElMessage.info('密码重置功能正在开发中')
  return
}

function resetPassword() {
  if (!forgotForm.value.code || !forgotForm.value.newPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }
  // 密码重置功能正在开发中
  ElMessage.info('密码重置功能正在开发中')
  return
}

function showTerms() {
  ElMessage.info('服务条款功能开发中')
}

function showPrivacy() {
  ElMessage.info('隐私政策功能开发中')
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 28%),
    radial-gradient(circle at bottom left, rgba(15, 118, 110, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.login-container::before,
.login-container::after {
  content: none;
}

.login-box {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
}

/* 返回首页 */
.back-home {
  margin-bottom: 20px;
  text-align: center;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #334155;
  text-decoration: none;
  font-size: 14px;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.2);
  backdrop-filter: blur(10px);
}

.back-link:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #0f172a;
}

/* Logo 区域 */
.login-header {
  text-align: center;
  margin-bottom: 32px;
  color: #0f172a;
}

.logo-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100px;
  height: 100px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  margin-bottom: 20px;
  backdrop-filter: blur(10px);
  cursor: pointer;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.logo-wrapper:hover {
  transform: scale(1.05);
  background: #fff;
}

.login-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px;
  color: #0f172a;
  letter-spacing: 0;
}

.login-subtitle {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

/* 登录卡片 */
.login-card {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: #e4e7ed;
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  height: 50px;
  line-height: 50px;
}

.login-form {
  padding: 24px 0 16px;
}

.login-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 4px 15px;
}

.password-toggle {
  cursor: pointer;
  color: #909399;
  transition: color 0.3s;
}

.password-toggle:hover {
  color: #2563eb;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-link {
  font-size: 13px;
}

.login-button {
  width: 100%;
  height: 44px;
  font-size: 15px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
  border: none;
}

.login-button:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0f6b66 100%);
}

/* 社交登录 */
.social-login {
  padding: 0 20px 20px;
}

.divider {
  display: flex;
  align-items: center;
  margin: 20px 0;
  color: #909399;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e4e7ed;
}

.divider span {
  padding: 0 16px;
}

.social-icons {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.social-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
  background: #f5f7fa;
  color: #606266;
}

.social-icon:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.social-icon.wechat:hover {
  background: #07c160;
  color: #fff;
}

.social-icon.qq:hover {
  background: #12b7f5;
  color: #fff;
}

.social-icon.workwechat:hover {
  background: #2bad31;
  color: #fff;
}

/* 注册协议 */
.register-agreement {
  padding: 0 20px 20px;
  text-align: center;
}

.register-agreement :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #606266;
}

/* 页脚 */
.login-footer {
  text-align: center;
  margin-top: 32px;
  color: #64748b;
}

.login-footer p {
  font-size: 13px;
  margin: 0 0 12px;
}

.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.footer-links a {
  color: #475569;
  text-decoration: none;
  transition: color 0.3s;
}

.footer-links a:hover {
  color: #0f172a;
}

.footer-links .divider {
  margin: 0;
  color: #cbd5e1;
}

.footer-links .divider::before,
.footer-links .divider::after {
  display: none;
}

/* 过期提示 */
.expired-alert {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 90%;
  max-width: 420px;
}

/* 忘记密码对话框 */
.forgot-steps {
  margin-bottom: 24px;
}

.forgot-content {
  padding: 20px 0;
  text-align: center;
}

.forgot-tip {
  color: #606266;
  margin-bottom: 20px;
}

.forgot-input {
  margin-bottom: 16px;
}

.forgot-btn {
  width: 100%;
  margin-top: 8px;
}

.forgot-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.success-text {
  font-size: 18px;
  font-weight: 600;
  color: #67c23a;
  margin: 0;
}

.success-tip {
  color: #909399;
  margin: 0 0 16px;
}

/* 响应式适配 */
@media (max-width: 480px) {
  .login-box {
    max-width: 100%;
  }
  
  .login-title {
    font-size: 26px;
  }
  
  .logo-wrapper {
    width: 80px;
    height: 80px;
  }
  
  .login-form {
    padding: 20px 0 12px;
  }
  
  .social-login {
    padding: 0 16px 16px;
  }
  
  .register-agreement {
    padding: 0 16px 16px;
  }
  
  .login-options {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}
</style>
