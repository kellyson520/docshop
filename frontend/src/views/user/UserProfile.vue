<template>
  <div class="user-profile">
    <el-page-header title="个人中心" @back="$router.back()" />
    
    <el-tabs v-model="activeTab" class="profile-tabs" type="border-card">
      <!-- 个人信息 -->
      <el-tab-pane label="个人信息" name="profile">
        <div class="tab-content">
          <el-row :gutter="24">
            <el-col :xs="24" :md="8">
              <el-card class="profile-card" shadow="hover">
                <div class="profile-header">
                  <el-avatar :size="100" :src="userInfo.avatar" class="profile-avatar">
                    <el-icon :size="48"><UserFilled /></el-icon>
                  </el-avatar>
                  <h3 class="profile-name">{{ userInfo.username }}</h3>
                  <el-tag :type="userInfo.role === 'admin' ? 'danger' : 'primary'" effect="dark" round>
                    {{ userInfo.role === 'admin' ? '管理员' : '普通用户' }}
                  </el-tag>
                  <p class="profile-join">注册于 {{ formatDate(userInfo.createdAt) }}</p>
                </div>
                <el-divider />
                <div class="profile-stats">
                  <div class="stat-item">
                    <span class="stat-value">{{ userInfo.projectCount }}</span>
                    <span class="stat-label">项目</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ userInfo.fileCount }}</span>
                    <span class="stat-label">文件</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ userInfo.downloadCount }}</span>
                    <span class="stat-label">下载</span>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :md="16">
              <el-card class="info-card" shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>基本信息</span>
                    <el-button type="primary" text @click="startEdit">
                      <el-icon><Edit /></el-icon>
                      编辑
                    </el-button>
                  </div>
                </template>
                
                <el-form :model="editForm" label-width="100px" :disabled="!isEditing">
                  <el-form-item label="用户名">
                    <el-input v-model="editForm.username" disabled />
                  </el-form-item>
                  <el-form-item label="昵称">
                    <el-input v-model="editForm.nickname" placeholder="请输入昵称" />
                  </el-form-item>
                  <el-form-item label="邮箱">
                    <el-input v-model="editForm.email" placeholder="请输入邮箱" />
                  </el-form-item>
                  <el-form-item label="手机号">
                    <el-input v-model="editForm.phone" placeholder="请输入手机号" />
                  </el-form-item>
                  <el-form-item label="个人简介">
                    <el-input 
                      v-model="editForm.bio" 
                      type="textarea" 
                      :rows="4" 
                      placeholder="介绍一下自己..."
                    />
                  </el-form-item>
                </el-form>
                
                <div v-if="isEditing" class="form-actions">
                  <el-button @click="cancelEdit">取消</el-button>
                  <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- 最近活动 -->
      <el-tab-pane label="最近活动" name="activities">
        <div class="tab-content">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>最近操作记录</span>
                <el-button text @click="$router.push('/activities')">
                  查看全部
                  <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                </el-button>
              </div>
            </template>
            
            <el-timeline>
              <el-timeline-item
                v-for="(activity, index) in recentActivities"
                :key="index"
                :type="activity.type"
                :timestamp="activity.time"
                :icon="getActivityIcon(activity.action)"
              >
                <div class="activity-item">
                  <span class="activity-action">{{ activity.description }}</span>
                  <el-tag v-if="activity.projectName" size="small" type="info">
                    {{ activity.projectName }}
                  </el-tag>
                </div>
              </el-timeline-item>
            </el-timeline>
            
            <el-empty v-if="recentActivities.length === 0" description="暂无活动记录" />
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 安全设置 -->
      <el-tab-pane label="安全设置" name="security">
        <div class="tab-content">
          <el-card shadow="hover" class="security-card">
            <template #header>
              <div class="card-header">
                <span>账户安全</span>
              </div>
            </template>
            
            <div class="security-list">
              <div class="security-item">
                <div class="security-info">
                  <el-icon :size="24" color="#67c23a"><Lock /></el-icon>
                  <div class="security-text">
                    <h4>登录密码</h4>
                    <p>建议定期更换密码以保护账户安全</p>
                  </div>
                </div>
                <el-button @click="showPasswordDialog = true">修改密码</el-button>
              </div>
              
              <el-divider />
              
              <div class="security-item">
                <div class="security-info">
                  <el-icon :size="24" :color="userInfo.email ? '#67c23a' : '#909399'"><Message /></el-icon>
                  <div class="security-text">
                    <h4>绑定邮箱</h4>
                    <p>{{ userInfo.email ? `已绑定：${maskEmail(userInfo.email)}` : '绑定邮箱可用于找回密码和接收通知' }}</p>
                  </div>
                </div>
                <el-button :type="userInfo.email ? '' : 'primary'" @click="showEmailDialog = true">
                  {{ userInfo.email ? '更换邮箱' : '绑定邮箱' }}
                </el-button>
              </div>
              
              <el-divider />
              
              <div class="security-item">
                <div class="security-info">
                  <el-icon :size="24" :color="userInfo.phone ? '#67c23a' : '#909399'"><Phone /></el-icon>
                  <div class="security-text">
                    <h4>绑定手机</h4>
                    <p>{{ userInfo.phone ? `已绑定：${maskPhone(userInfo.phone)}` : '绑定手机可用于登录和接收安全提醒' }}</p>
                  </div>
                </div>
                <el-button :type="userInfo.phone ? '' : 'primary'" @click="showPhoneDialog = true">
                  {{ userInfo.phone ? '更换手机' : '绑定手机' }}
                </el-button>
              </div>
              
              <el-divider />
              
              <div class="security-item">
                <div class="security-info">
                  <el-icon :size="24" color="#e6a23c"><Warning /></el-icon>
                  <div class="security-text">
                    <h4>登录设备管理</h4>
                    <p>查看和管理已登录的设备</p>
                  </div>
                </div>
                <el-button @click="showDevicesDialog = true">管理设备</el-button>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="400px" destroy-on-close>
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px">
        <el-form-item label="当前密码" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="changePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 绑定邮箱对话框 -->
    <el-dialog v-model="showEmailDialog" title="绑定邮箱" width="400px" destroy-on-close>
      <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" label-width="80px">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="emailForm.email" placeholder="请输入邮箱地址" />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <el-input v-model="emailForm.code" placeholder="请输入验证码">
            <template #append>
              <el-button :disabled="codeSending || countdown > 0" @click="sendCode">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEmailDialog = false">取消</el-button>
        <el-button type="primary" :loading="emailLoading" @click="bindEmail">确认绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  UserFilled, Edit, ArrowRight, Lock, Message, Phone, Warning,
  Upload, Download, Plus, Delete, EditPen, View, Star
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const activeTab = ref('profile')
const isEditing = ref(false)
const saving = ref(false)

const userInfo = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  bio: '',
  avatar: '',
  role: 'user',
  createdAt: '',
  projectCount: 12,
  fileCount: 156,
  downloadCount: 2340
})

const editForm = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  bio: ''
})

const recentActivities = ref([
  {
    action: 'upload',
    description: '上传了新文件',
    projectName: '项目A',
    time: '2024-01-15 14:30',
    type: 'primary'
  },
  {
    action: 'create',
    description: '创建了新项目',
    projectName: '项目B',
    time: '2024-01-15 10:20',
    type: 'success'
  },
  {
    action: 'download',
    description: '下载了文件',
    projectName: '项目A',
    time: '2024-01-14 16:45',
    type: 'warning'
  },
  {
    action: 'diff',
    description: '执行了版本对比',
    projectName: '项目C',
    time: '2024-01-14 09:15',
    type: 'info'
  },
  {
    action: 'share',
    description: '分享了项目链接',
    projectName: '项目A',
    time: '2024-01-13 11:30',
    type: 'primary'
  }
])

// 密码修改
const showPasswordDialog = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref(null)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 邮箱绑定
const showEmailDialog = ref(false)
const emailLoading = ref(false)
const codeSending = ref(false)
const countdown = ref(0)
const emailFormRef = ref(null)
const emailForm = reactive({
  email: '',
  code: ''
})

const emailRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

// 设备管理
const showDevicesDialog = ref(false)
const showPhoneDialog = ref(false)

onMounted(() => {
  // 从 authStore 获取用户信息
  if (authStore.user) {
    userInfo.username = authStore.user.username || '用户'
    userInfo.role = authStore.user.is_admin ? 'admin' : 'user'
    userInfo.createdAt = authStore.user.created_at || new Date().toISOString()
    
    // 初始化编辑表单
    editForm.username = userInfo.username
    editForm.nickname = userInfo.nickname || ''
    editForm.email = userInfo.email || ''
    editForm.phone = userInfo.phone || ''
    editForm.bio = userInfo.bio || ''
  }
})

function startEdit() {
  isEditing.value = true
  Object.assign(editForm, {
    nickname: userInfo.nickname,
    email: userInfo.email,
    phone: userInfo.phone,
    bio: userInfo.bio
  })
}

function cancelEdit() {
  isEditing.value = false
}

async function saveProfile() {
  saving.value = true
  try {
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1000))
    Object.assign(userInfo, editForm)
    isEditing.value = false
    ElMessage.success('保存成功')
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  passwordLoading.value = true
  try {
    // 模拟修改密码
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('密码修改成功')
    showPasswordDialog.value = false
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } finally {
    passwordLoading.value = false
  }
}

async function sendCode() {
  const valid = await emailFormRef.value?.validateField('email').catch(() => false)
  if (!valid) return
  
  codeSending.value = true
  try {
    // 模拟发送验证码
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } finally {
    codeSending.value = false
  }
}

async function bindEmail() {
  const valid = await emailFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  emailLoading.value = true
  try {
    // 模拟绑定邮箱
    await new Promise(resolve => setTimeout(resolve, 1000))
    userInfo.email = emailForm.email
    ElMessage.success('邮箱绑定成功')
    showEmailDialog.value = false
    emailForm.email = ''
    emailForm.code = ''
  } finally {
    emailLoading.value = false
  }
}

function getActivityIcon(action) {
  const iconMap = {
    upload: 'Upload',
    download: 'Download',
    create: 'Plus',
    delete: 'Delete',
    edit: 'EditPen',
    diff: 'View',
    share: 'Share'
  }
  return iconMap[action] || 'CircleCheck'
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function maskEmail(email) {
  if (!email) return ''
  const [name, domain] = email.split('@')
  const maskedName = name.slice(0, 2) + '***'
  return `${maskedName}@${domain}`
}

function maskPhone(phone) {
  if (!phone) return ''
  return phone.slice(0, 3) + '****' + phone.slice(-4)
}
</script>

<style scoped>
.user-profile {
  padding: 20px;
}

.profile-tabs {
  margin-top: 20px;
}

.tab-content {
  padding: 20px 0;
}

/* 个人信息卡片 */
.profile-card {
  text-align: center;
}

.profile-header {
  padding: 20px 0;
}

.profile-avatar {
  margin-bottom: 16px;
  border: 4px solid #f0f2f5;
}

.profile-name {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 12px;
}

.profile-join {
  font-size: 13px;
  color: var(--text-secondary, #909399);
  margin: 12px 0 0;
}

.profile-stats {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

/* 信息卡片 */
.info-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

/* 活动列表 */
.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.activity-action {
  font-size: 14px;
  color: var(--text-primary, #303133);
}

/* 安全设置 */
.security-card {
  max-width: 800px;
}

.security-list {
  padding: 10px 0;
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.security-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.security-text h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 4px;
}

.security-text p {
  font-size: 13px;
  color: var(--text-secondary, #909399);
  margin: 0;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .user-profile {
    padding: 12px;
  }

  .profile-card {
    margin-bottom: 20px;
  }

  .security-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}

/* 暗色模式适配 */
[data-theme="dark"] .profile-avatar {
  border-color: #2c2c2c;
}
</style>
