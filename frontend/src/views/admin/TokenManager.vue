<template>
  <div class="access-page">
    <PageHeader
      title="用户与令牌"
      subtitle="集中管理登录账号、权限角色、自助注册和访问令牌"
      :breadcrumbs="[{ title: '用户与令牌' }]"
    >
      <template #actions>
        <el-button v-if="activeTab === 'users'" type="primary" @click="openCreateUser">
          <el-icon><Plus /></el-icon>
          新建用户
        </el-button>
        <el-button v-else type="primary" @click="openCreateToken">
          <el-icon><Plus /></el-icon>
          生成令牌
        </el-button>
      </template>
    </PageHeader>

    <section class="security-band">
      <div>
        <p class="band-label">站点门禁</p>
        <h3>未登录用户已被拦截</h3>
        <p>除登录页外，前端路由必须持有有效登录 token。自助注册可在这里统一开关。</p>
      </div>
      <div class="security-actions">
        <span class="switch-text">{{ registrationEnabled ? '允许自助注册' : '仅管理员创建用户' }}</span>
        <el-switch
          v-model="registrationEnabled"
          :loading="securityLoading"
          active-text="开启"
          inactive-text="关闭"
          @change="saveRegistrationSwitch"
        />
      </div>
    </section>

    <div class="stat-grid">
      <div class="stat-item">
        <span>用户总数</span>
        <strong>{{ userStats.total || 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>管理员</span>
        <strong>{{ userStats.admins || 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>普通用户</span>
        <strong>{{ userStats.users || 0 }}</strong>
      </div>
      <div class="stat-item">
        <span>有效令牌</span>
        <strong>{{ activeTokenCount }}</strong>
      </div>
    </div>

    <el-card shadow="never" class="access-panel">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="用户管理" name="users">
          <el-table v-loading="usersLoading" :data="users" stripe>
            <el-table-column prop="username" label="账号" min-width="180">
              <template #default="{ row }">
                <div class="user-cell">
                  <el-avatar :size="30">{{ row.username?.slice(0, 1)?.toUpperCase() }}</el-avatar>
                  <div>
                    <strong>{{ row.username }}</strong>
                    <span>{{ row.id }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="权限" width="180">
              <template #default="{ row }">
                <el-select v-model="row.role" size="small" @change="changeUserRole(row)">
                  <el-option label="管理员" value="admin" />
                  <el-option label="普通用户" value="user" />
                  <el-option label="只读用户" value="viewer" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="角色说明" min-width="220">
              <template #default="{ row }">
                <el-tag :type="roleMeta(row.role).type" effect="plain">{{ roleMeta(row.role).label }}</el-tag>
                <span class="role-desc">{{ roleMeta(row.role).desc }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button text size="small" @click="openResetPassword(row)">
                  <el-icon><Lock /></el-icon>
                  重置密码
                </el-button>
                <el-button text type="danger" size="small" @click="removeUser(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="访问令牌" name="tokens">
          <el-table v-loading="tokensLoading" :data="tokens" stripe>
            <el-table-column prop="name" label="名称" width="180" />
            <el-table-column label="令牌" min-width="320">
              <template #default="{ row }">
                <div class="token-cell">
                  <code>{{ row.token }}</code>
                  <el-tooltip content="复制令牌" placement="top">
                    <el-button text size="small" @click="copy(row.token)">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active === 1" @change="toggleToken(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button text size="small" @click="regenerateToken(row)">
                  <el-icon><Refresh /></el-icon>
                  重生成
                </el-button>
                <el-button text type="danger" size="small" @click="removeToken(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="userDialogVisible" title="新建用户" width="460px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="账号">
          <el-input v-model="userForm.username" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="userForm.password" type="password" show-password placeholder="至少 8 位，包含字母和数字" />
        </el-form-item>
        <el-form-item label="权限角色">
          <el-segmented v-model="userForm.role" :options="roleOptions" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="createUser">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordDialogVisible" title="重置密码" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="passwordTarget ? `账号：${passwordTarget.username}` : '账号'">
          <el-input v-model="newPassword" type="password" show-password placeholder="至少 8 位，包含字母和数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="resetPassword">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tokenDialogVisible" title="生成访问令牌" width="420px" destroy-on-close>
      <el-input v-model="tokenName" placeholder="令牌名称" />
      <template #footer>
        <el-button @click="tokenDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingToken" @click="createToken">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Lock, Plus, Refresh } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import PageHeader from '@/components/common/PageHeader.vue'

const activeTab = ref('users')
const users = ref([])
const tokens = ref([])
const userStats = ref({})
const usersLoading = ref(false)
const tokensLoading = ref(false)
const securityLoading = ref(false)
const savingUser = ref(false)
const savingToken = ref(false)

const registrationEnabled = ref(false)
const userDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const tokenDialogVisible = ref(false)
const passwordTarget = ref(null)
const newPassword = ref('')
const tokenName = ref('')

const userForm = ref({
  username: '',
  password: '',
  role: 'user'
})

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '普通用户', value: 'user' },
  { label: '只读用户', value: 'viewer' }
]

const activeTokenCount = computed(() => tokens.value.filter((token) => token.is_active === 1).length)

function roleMeta(role) {
  const map = {
    admin: { label: '管理员', type: 'danger', desc: '可管理项目、用户、令牌和系统配置' },
    user: { label: '普通用户', type: 'primary', desc: '可登录并使用普通业务功能' },
    viewer: { label: '只读用户', type: 'info', desc: '保留账号权限，限制管理操作' }
  }
  return map[role] || map.viewer
}

async function fetchUsers() {
  usersLoading.value = true
  try {
    const data = await get('/users')
    users.value = data.items || []
    userStats.value = data.stats || {}
  } finally {
    usersLoading.value = false
  }
}

async function fetchTokens() {
  tokensLoading.value = true
  try {
    const data = await get('/access-tokens')
    tokens.value = data.items || []
  } finally {
    tokensLoading.value = false
  }
}

async function fetchRegistrationSwitch() {
  securityLoading.value = true
  try {
    const data = await get('/users/settings/registration')
    registrationEnabled.value = !!data.registration_enabled
  } finally {
    securityLoading.value = false
  }
}

async function saveRegistrationSwitch() {
  securityLoading.value = true
  try {
    const data = await put('/users/settings/registration', { registration_enabled: registrationEnabled.value })
    registrationEnabled.value = !!data.registration_enabled
    ElMessage.success(registrationEnabled.value ? '已开启自助注册' : '已关闭自助注册')
  } finally {
    securityLoading.value = false
  }
}

function handleTabChange(tab) {
  if (tab === 'users') fetchUsers()
  if (tab === 'tokens') fetchTokens()
}

function openCreateUser() {
  userForm.value = { username: '', password: '', role: 'user' }
  userDialogVisible.value = true
}

async function createUser() {
  savingUser.value = true
  try {
    await post('/users', userForm.value)
    ElMessage.success('用户已创建')
    userDialogVisible.value = false
    fetchUsers()
  } finally {
    savingUser.value = false
  }
}

async function changeUserRole(row) {
  try {
    await put(`/users/${row.id}`, { role: row.role })
    ElMessage.success('权限已更新')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.message || '权限更新失败')
    fetchUsers()
  }
}

function openResetPassword(row) {
  passwordTarget.value = row
  newPassword.value = ''
  passwordDialogVisible.value = true
}

async function resetPassword() {
  if (!passwordTarget.value) return
  savingUser.value = true
  try {
    await put(`/users/${passwordTarget.value.id}`, { password: newPassword.value })
    ElMessage.success('密码已重置')
    passwordDialogVisible.value = false
  } finally {
    savingUser.value = false
  }
}

async function removeUser(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除用户', { type: 'warning' })
  } catch {
    return
  }
  await del(`/users/${row.id}`)
  ElMessage.success('用户已删除')
  fetchUsers()
}

function openCreateToken() {
  tokenName.value = '主页访问'
  tokenDialogVisible.value = true
}

async function createToken() {
  savingToken.value = true
  try {
    await post('/access-tokens', { name: tokenName.value })
    ElMessage.success('令牌已生成')
    tokenDialogVisible.value = false
    fetchTokens()
  } finally {
    savingToken.value = false
  }
}

async function toggleToken(row) {
  await put(`/access-tokens/${row.id}`, { is_active: row.is_active === 1 ? 0 : 1 })
  row.is_active = row.is_active === 1 ? 0 : 1
}

async function regenerateToken(row) {
  await put(`/access-tokens/${row.id}`, { regenerate: true })
  ElMessage.success('令牌已重新生成')
  fetchTokens()
}

async function removeToken(row) {
  try {
    await ElMessageBox.confirm(`确定删除令牌「${row.name}」吗？`, '删除令牌', { type: 'warning' })
  } catch {
    return
  }
  await del(`/access-tokens/${row.id}`)
  ElMessage.success('令牌已删除')
  fetchTokens()
}

function copy(text) {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制')
}

onMounted(() => {
  fetchRegistrationSwitch()
  fetchUsers()
  fetchTokens()
})
</script>

<style scoped>
.access-page {
  max-width: 1240px;
  margin: 0 auto;
}

.security-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 20px;
  margin-bottom: 16px;
  border: 1px solid #d7dde8;
  border-radius: 8px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef4ff 100%);
}

.band-label {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.security-band h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 18px;
}

.security-band p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.security-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.switch-text {
  color: #334155;
  font-size: 13px;
  font-weight: 600;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  min-height: 78px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.stat-item span {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 8px;
}

.stat-item strong {
  color: #0f172a;
  font-size: 28px;
  line-height: 1;
}

.access-panel {
  border-radius: 8px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-cell strong {
  display: block;
  color: #111827;
  font-size: 14px;
}

.user-cell span {
  display: block;
  max-width: 260px;
  overflow: hidden;
  color: #94a3b8;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-desc {
  margin-left: 8px;
  color: #64748b;
  font-size: 12px;
}

.token-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-cell code {
  max-width: 520px;
  overflow-wrap: anywhere;
  color: #334155;
  font-size: 12px;
}

@media (max-width: 760px) {
  .security-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
