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
        <el-button v-else-if="activeTab === 'tokens'" type="primary" @click="openCreateToken">
          <el-icon><Plus /></el-icon>
          生成令牌
        </el-button>
        <el-button v-else-if="activeTab === 'shareTokens'" type="primary" plain :loading="shareTokensLoading" @click="fetchShareTokens">
          <el-icon><Refresh /></el-icon>
          刷新分享令牌
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
        <strong>{{ tokensLoaded ? activeTokenCount : '—' }}</strong>
      </div>
    </div>

    <el-card shadow="never" class="access-panel">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="用户管理" name="users" lazy>
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

        <el-tab-pane label="访问令牌" name="tokens" lazy>
          <el-table v-loading="tokensLoading" :data="tokens" stripe>
            <el-table-column prop="name" label="名称" width="180" />
            <el-table-column label="令牌" min-width="320">
              <template #default="{ row }">
                <div class="token-cell">
                  <code>{{ displayToken(row) }}</code>
                  <el-tooltip content="复制访问链接" placement="top">
                    <el-button text size="small" :loading="copyingTokenId === row.id" @click="copyAccessLink(row)">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active === 1" @change="(enabled) => toggleToken(row, enabled)" />
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

        <el-tab-pane label="分享令牌" name="shareTokens" lazy>
          <div class="share-token-toolbar">
            <p class="share-token-hint">
              这里集中管理“分享项目 / 分享文件”生成的分享令牌，可统一复制、启停、编辑、重生成和删除。
            </p>
            <el-button :loading="shareTokensLoading" @click="fetchShareTokens">
              <el-icon><Refresh /></el-icon>
              刷新列表
            </el-button>
          </div>

          <el-table v-loading="shareTokensLoading" :data="shareTokens" stripe>
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column label="资源" min-width="220">
              <template #default="{ row }">
                <div class="share-resource-cell">
                  <el-tag size="small" effect="plain">{{ shareResourceLabel(row.resource_type) }}</el-tag>
                  <span class="share-resource-id">{{ row.resource_id || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="分享链接" min-width="340">
              <template #default="{ row }">
                <div class="token-cell">
                  <code>{{ displayShareToken(row) }}</code>
                  <el-tooltip content="复制分享链接" placement="top">
                    <el-button text size="small" :loading="copyingShareTokenId === row.id" @click="copyShareLink(row)">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="限制" min-width="220">
              <template #default="{ row }">
                <div class="share-limit-cell">
                  <span>浏览 {{ row.view_count || 0 }} / {{ row.max_views || '∞' }}</span>
                  <span>下载 {{ row.download_count || 0 }} / {{ row.max_downloads || '∞' }}</span>
                  <span>{{ row.expires_at ? `到期：${row.expires_at}` : '长期有效' }}</span>
                  <el-button text size="small" @click="openShareRestrictionDialog(row)">
                    权限详情
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active === 1" @change="(enabled) => toggleShareToken(row, enabled)" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button text size="small" @click="openShareTokenEditor(row)">
                  编辑
                </el-button>
                <el-button text size="small" @click="regenerateManagedShareToken(row)">
                  <el-icon><Refresh /></el-icon>
                  重生成
                </el-button>
                <el-button text type="danger" size="small" @click="removeManagedShareToken(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="分享策略" name="sharePolicy" lazy>
          <el-form v-loading="sharePolicyLoading" label-position="top" class="policy-form">
            <el-form-item label="启用分享">
              <el-switch v-model="sharePolicy.enabled" active-text="开启" inactive-text="关闭" />
            </el-form-item>
            <el-form-item label="允许登录用户创建分享">
              <el-switch v-model="sharePolicy.allow_user_creation" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许未登录访客创建分享">
              <el-switch v-model="sharePolicy.allow_anonymous_creation" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许分享的资源类型">
              <el-checkbox-group v-model="sharePolicy.allowed_resource_types">
                <el-checkbox label="project">项目</el-checkbox>
                <el-checkbox label="file">文件</el-checkbox>
                <el-checkbox label="version">版本</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <div class="share-limit-grid">
              <el-form-item label="默认查看次数上限（0 为不限）">
                <el-input-number v-model="sharePolicy.default_max_views" :min="0" />
              </el-form-item>
              <el-form-item label="默认下载次数上限（0 为不限）">
                <el-input-number v-model="sharePolicy.default_max_downloads" :min="0" />
              </el-form-item>
            </div>
            <el-form-item label="默认允许下载">
              <el-switch v-model="sharePolicy.default_allow_download" />
            </el-form-item>
            <el-form-item label="最长有效期天数（0 为不限）">
              <el-input-number v-model="sharePolicy.max_expiry_days" :min="0" />
            </el-form-item>
            <el-button type="primary" :loading="sharePolicyLoading" @click="saveSharePolicy">
              保存分享策略
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="userDialogVisible" title="新建用户" width="460px" v-bind="ADMIN_VIEWPORT_DIALOG_PROPS" class="admin-viewport-dialog" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="账号">
          <el-input v-model="userForm.username" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
            placeholder="至少 8 位，包含字母和数字"
          />
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

    <el-dialog v-model="passwordDialogVisible" title="重置密码" width="420px" v-bind="ADMIN_VIEWPORT_DIALOG_PROPS" class="admin-viewport-dialog" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="passwordTarget ? `账号：${passwordTarget.username}` : '账号'">
          <el-input
            v-model="newPassword"
            type="password"
            show-password
            placeholder="至少 8 位，包含字母和数字"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="resetPassword">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tokenDialogVisible" title="生成访问令牌" width="420px" v-bind="ADMIN_VIEWPORT_DIALOG_PROPS" class="admin-viewport-dialog" destroy-on-close>
      <el-input v-model="tokenName" placeholder="令牌名称" />
      <template #footer>
        <el-button @click="tokenDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingToken" @click="createToken">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shareTokenDialogVisible" title="编辑分享令牌" width="560px" v-bind="ADMIN_VIEWPORT_DIALOG_PROPS" class="admin-viewport-dialog" destroy-on-close>
      <el-form label-position="top" class="policy-form">
        <el-form-item label="名称">
          <el-input v-model="shareTokenForm.name" placeholder="分享令牌名称" />
        </el-form-item>
        <div class="share-limit-grid">
          <el-form-item label="最大浏览次数">
            <el-input-number v-model="shareTokenForm.max_views" :min="0" />
          </el-form-item>
          <el-form-item label="最大下载次数">
            <el-input-number v-model="shareTokenForm.max_downloads" :min="0" />
          </el-form-item>
        </div>
        <el-form-item label="允许下载">
          <el-switch v-model="shareTokenForm.allow_download" active-text="允许" inactive-text="禁止" />
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="shareTokenForm.expires_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="不设置则长期有效"
            style="width: 100%"
          />
        </el-form-item>
        <div class="share-access-section">
          <div class="share-access-section__title">访问与权限控制</div>
          <p class="share-access-section__summary">分享权限仅作用于分享链接，不继承公开浏览权限。</p>
          <div class="share-access-grid">
            <el-form-item label="需要登录">
              <el-switch v-model="shareTokenForm.require_login" active-text="是" inactive-text="否" />
            </el-form-item>
            <el-form-item label="允许预览">
              <el-switch v-model="shareTokenForm.allow_preview" active-text="允许" inactive-text="禁用" />
            </el-form-item>
            <el-form-item label="允许 Diff">
              <el-switch v-model="shareTokenForm.allow_diff" active-text="允许" inactive-text="禁用" />
            </el-form-item>
            <el-form-item label="允许版本历史">
              <el-switch v-model="shareTokenForm.allow_versions" active-text="允许" inactive-text="禁用" />
            </el-form-item>
          </div>
          <div class="share-access-grid">
            <el-form-item label="访问密码">
              <el-input
                v-model="shareTokenForm.password"
                type="password"
                show-password
                placeholder="留空表示保留当前密码"
              />
              <div class="share-field-note">只有填写新密码时才会覆盖当前密码。</div>
            </el-form-item>
            <el-form-item label="密码提示">
              <el-input v-model="shareTokenForm.password_hint" placeholder="可选，给访问者的提示" />
            </el-form-item>
          </div>
          <el-form-item label="清除现有密码">
            <el-switch
              v-model="shareTokenForm.clear_password"
              :disabled="Boolean(shareTokenForm.password)"
              active-text="清除"
              inactive-text="保留"
            />
            <div class="share-field-note">如需改成无密码访问，请先留空“访问密码”，再打开这个开关。</div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="shareTokenDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingShareToken" @click="saveShareToken">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="shareRestrictionDialogVisible"
      title="权限详情"
      width="520px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog restriction-detail-dialog"
      destroy-on-close
    >
      <div v-if="shareRestrictionTarget" class="share-limit-cell">
        <span>名称：{{ shareRestrictionTarget.name || '-' }}</span>
        <span>资源：{{ shareResourceLabel(shareRestrictionTarget.resource_type) }} / {{ shareRestrictionTarget.resource_id || '-' }}</span>
        <span>浏览：{{ shareRestrictionTarget.view_count || 0 }} / {{ shareRestrictionTarget.max_views || '∞' }}</span>
        <span>下载：{{ shareRestrictionTarget.download_count || 0 }} / {{ shareRestrictionTarget.max_downloads || '∞' }}</span>
        <span>{{ shareRestrictionTarget.expires_at ? `到期：${shareRestrictionTarget.expires_at}` : '长期有效' }}</span>
        <span v-for="item in shareRestrictionSummaryItems" :key="item.key">{{ item.text }}</span>
      </div>
      <template #footer>
        <el-button @click="shareRestrictionDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Lock, Plus, Refresh } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import {
  deleteShareToken,
  getSharePolicy,
  listShareTokens,
  regenerateShareToken,
  updateSharePolicy,
  updateShareToken,
} from '@/api/share'
import { copyToClipboard } from '@/utils'
import PageHeader from '@/components/common/PageHeader.vue'
import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'
import {
  buildShareAccessSummaryItems,
} from '@/utils/shareAccess'
import { buildShareUrl } from '@/utils/previewManagement'
import { buildShareTokenFormState, buildShareTokenMutationPayload } from '@/utils/shareTokenForm'

const activeTab = ref('users')
const users = ref([])
const tokens = ref([])
const shareTokens = ref([])
const userStats = ref({})
const usersLoading = ref(false)
const tokensLoading = ref(false)
const shareTokensLoading = ref(false)
const sharePolicyLoading = ref(false)
const sharePolicy = ref({
  enabled: true,
  allow_user_creation: true,
  allow_anonymous_creation: false,
  allowed_resource_types: ['project', 'file', 'version'],
  default_max_views: 0,
  default_max_downloads: 0,
  default_allow_download: true,
  max_expiry_days: 0
})
const usersLoaded = ref(false)
const tokensLoaded = ref(false)
const shareTokensLoaded = ref(false)
const sharePolicyLoaded = ref(false)
const securityLoading = ref(false)
const savingUser = ref(false)
const savingToken = ref(false)
const savingShareToken = ref(false)

const registrationEnabled = ref(false)
const userDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const tokenDialogVisible = ref(false)
const shareTokenDialogVisible = ref(false)
const shareRestrictionDialogVisible = ref(false)
const copyingTokenId = ref('')
const copyingShareTokenId = ref('')
const passwordTarget = ref(null)
const editingShareToken = ref(null)
const shareRestrictionTarget = ref(null)
const newPassword = ref('')
const tokenName = ref('')
const shareTokenForm = ref(buildShareTokenFormState())
let registrationSwitchRequestId = 0

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
const shareRestrictionSummaryItems = computed(() => (
  shareRestrictionTarget.value ? buildShareAccessSummaryItems(shareRestrictionTarget.value) : []
))

function roleMeta(role) {
  const map = {
    admin: { label: '管理员', type: 'danger', desc: '可管理项目、用户、令牌和系统配置' },
    user: { label: '普通用户', type: 'primary', desc: '可登录并使用普通业务功能' },
    viewer: { label: '只读用户', type: 'info', desc: '保留账号权限，但限制管理操作' }
  }

  return map[role] || map.viewer
}

async function fetchUsers() {
  usersLoading.value = true
  try {
    const data = await get('/users')
    users.value = data.items || []
    userStats.value = data.stats || {}
    usersLoaded.value = true
  } finally {
    usersLoading.value = false
  }
}

async function fetchTokens() {
  tokensLoading.value = true
  try {
    const data = await get('/access-tokens')
    tokens.value = data.items || []
    tokensLoaded.value = true
  } finally {
    tokensLoading.value = false
  }
}

async function fetchShareTokens() {
  shareTokensLoading.value = true
  try {
    const data = await listShareTokens()
    shareTokens.value = data.items || []
    shareTokensLoaded.value = true
  } finally {
    shareTokensLoading.value = false
  }
}

async function fetchRegistrationSwitch() {
  const requestId = ++registrationSwitchRequestId
  securityLoading.value = true
  try {
    const data = await get('/users/settings/registration')
    if (requestId !== registrationSwitchRequestId) return
    registrationEnabled.value = !!data.registration_enabled
  } finally {
    if (requestId === registrationSwitchRequestId) {
      securityLoading.value = false
    }
  }
}

async function saveRegistrationSwitch() {
  const requestId = ++registrationSwitchRequestId
  securityLoading.value = true
  try {
    const data = await put('/users/settings/registration', { registration_enabled: registrationEnabled.value })
    if (requestId !== registrationSwitchRequestId) return
    registrationEnabled.value = !!data.registration_enabled
    ElMessage.success(registrationEnabled.value ? '已开启自助注册' : '已关闭自助注册')
  } finally {
    if (requestId === registrationSwitchRequestId) {
      securityLoading.value = false
    }
  }
}

async function handleTabChange(tab) {
  if (tab === 'users' && !usersLoaded.value) await fetchUsers()
  if (tab === 'tokens' && !tokensLoaded.value) await fetchTokens()
  if (tab === 'shareTokens' && !shareTokensLoaded.value) await fetchShareTokens()
  if (tab === 'sharePolicy' && !sharePolicyLoaded.value) await fetchSharePolicy()
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
    await fetchUsers()
  } finally {
    savingUser.value = false
  }
}

async function changeUserRole(row) {
  try {
    await put(`/users/${row.id}`, { role: row.role })
    ElMessage.success('权限已更新')
    await fetchUsers()
  } catch (err) {
    ElMessage.error(err.message || '权限更新失败')
    await fetchUsers()
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
  await fetchUsers()
}

function openCreateToken() {
  tokenName.value = '首页访问'
  tokenDialogVisible.value = true
}

async function createToken() {
  savingToken.value = true
  try {
    const data = await post('/access-tokens', { name: tokenName.value })
    ElMessage.success('令牌已生成')
    if (data?.token) {
      await ElMessageBox.alert(data.token, '请立即复制新令牌', {
        confirmButtonText: '我已保存',
        type: 'success'
      })
    }
    tokenDialogVisible.value = false
    await fetchTokens()
  } finally {
    savingToken.value = false
  }
}

async function toggleToken(row, enabled) {
  const previous = row.is_active
  const next = enabled ? 1 : 0

  try {
    await put(`/access-tokens/${row.id}`, { is_active: next })
    row.is_active = next
    ElMessage.success(next === 1 ? 'Token enabled' : 'Token disabled')
  } catch (err) {
    row.is_active = previous
    ElMessage.error(err.message || 'Failed to update token status')
  }
}

async function regenerateToken(row) {
  const data = await put(`/access-tokens/${row.id}`, { regenerate: true })
  ElMessage.success('令牌已重新生成')
  if (data?.token) {
    await ElMessageBox.alert(data.token, '请立即复制重生成令牌', {
      confirmButtonText: '我已保存',
      type: 'success'
    })
  }
  await fetchTokens()
}

function displayToken(row) {
  return row.token || row.token_preview || '****'
}

async function removeToken(row) {
  try {
    await ElMessageBox.confirm(`确定删除令牌「${row.name}」吗？`, '删除令牌', { type: 'warning' })
  } catch {
    return
  }

  await del(`/access-tokens/${row.id}`)
  ElMessage.success('令牌已删除')
  await fetchTokens()
}

function accessLink(token) {
  return `${window.location.origin}/?token=${encodeURIComponent(token)}`
}

function shareResourceLabel(type) {
  const map = {
    project: '项目',
    file: '文件',
    version: '版本',
  }
  return map[type] || type || '未知'
}

function shareLink(row) {
  if (row?.token) return buildShareUrl(row.token, window.location.origin)
  if (row?.share_url) return row.share_url.startsWith('http') ? row.share_url : `${window.location.origin}${row.share_url}`
  return ''
}

function displayShareToken(row) {
  return shareLink(row) || row?.token_preview || '****'
}

function shareAccessSummaryItems(row) {
  return buildShareAccessSummaryItems(row)
}

function openShareRestrictionDialog(row) {
  shareRestrictionTarget.value = row
  shareRestrictionDialogVisible.value = true
}

async function copyAccessLink(row) {
  if (!row?.id) {
    ElMessage.error('令牌信息缺失，无法复制访问链接')
    return
  }

  copyingTokenId.value = row.id
  try {
    let token = row.token
    if (!token) {
      const data = await get(`/access-tokens/${row.id}`)
      token = data?.token
      if (token) row.token = token
    }

    if (!token) {
      ElMessage.error('完整令牌获取失败，无法复制访问链接')
      return
    }

    const success = await copyToClipboard(accessLink(token))
    if (success) {
      ElMessage.success('访问链接已复制')
    } else {
      ElMessage.error('复制失败，请手动复制')
    }
  } catch (err) {
    ElMessage.error(err.message || '访问链接获取失败')
  } finally {
    copyingTokenId.value = ''
  }
}

async function copyShareLink(row) {
  const link = shareLink(row)
  if (!link) {
    ElMessage.error('分享链接缺失，无法复制')
    return
  }

  copyingShareTokenId.value = row.id
  try {
    const success = await copyToClipboard(link)
    if (success) {
      ElMessage.success('分享链接已复制')
    } else {
      ElMessage.error('复制失败，请手动复制')
    }
  } finally {
    copyingShareTokenId.value = ''
  }
}

async function toggleShareToken(row, enabled) {
  const previous = row.is_active
  const next = enabled ? 1 : 0

  try {
    await updateShareToken(row.id, { is_active: next })
    row.is_active = next
    ElMessage.success(next === 1 ? '分享令牌已启用' : '分享令牌已停用')
  } catch (err) {
    row.is_active = previous
    ElMessage.error(err.message || '分享令牌状态更新失败')
  }
}

function openShareTokenEditor(row) {
  editingShareToken.value = row
  shareTokenForm.value = buildShareTokenFormState({ token: row })
  shareTokenDialogVisible.value = true
}

async function saveShareToken() {
  if (!editingShareToken.value) return

  savingShareToken.value = true
  try {
    const payload = buildShareTokenMutationPayload(shareTokenForm.value, {
      preservePasswordWhenBlank: true,
      includeResourceIdentifiers: false,
    })
    await updateShareToken(editingShareToken.value.id, payload)
    shareTokenDialogVisible.value = false
    ElMessage.success('分享令牌已更新')
    await fetchShareTokens()
  } catch (err) {
    ElMessage.error(err.message || '分享令牌更新失败')
  } finally {
    savingShareToken.value = false
  }
}

async function regenerateManagedShareToken(row) {
  try {
    const data = await regenerateShareToken(row.id)
    const link = buildShareUrl(data.token, window.location.origin)
    await fetchShareTokens()
    await copyToClipboard(link)
    await ElMessageBox.alert(link, '新的分享链接', {
      confirmButtonText: '确定',
      type: 'success',
    })
  } catch (err) {
    ElMessage.error(err.message || '分享令牌重生成失败')
  }
}

async function removeManagedShareToken(row) {
  try {
    await ElMessageBox.confirm(`确定删除分享令牌「${row.name}」吗？`, '删除分享令牌', { type: 'warning' })
  } catch {
    return
  }

  try {
    await deleteShareToken(row.id)
    ElMessage.success('分享令牌已删除')
    await fetchShareTokens()
  } catch (err) {
    ElMessage.error(err.message || '分享令牌删除失败')
  }
}

async function fetchSharePolicy() {
  sharePolicyLoading.value = true
  try {
    sharePolicy.value = await getSharePolicy()
    sharePolicyLoaded.value = true
  } finally {
    sharePolicyLoading.value = false
  }
}

async function saveSharePolicy() {
  sharePolicyLoading.value = true
  try {
    sharePolicy.value = await updateSharePolicy(sharePolicy.value)
    sharePolicyLoaded.value = true
    ElMessage.success('分享策略已保存')
  } finally {
    sharePolicyLoading.value = false
  }
}

onMounted(() => {
  fetchRegistrationSwitch()
  fetchUsers()
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

.share-token-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.share-token-hint {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.share-resource-cell,
.share-limit-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.share-resource-id {
  color: #64748b;
  font-size: 12px;
  word-break: break-all;
}

.share-limit-cell {
  color: #475569;
  font-size: 12px;
}

.policy-form {
  max-width: 720px;
  padding: 10px 4px;
}

.share-limit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.share-limit-grid :deep(.el-input-number) {
  width: 100%;
}

.share-access-section {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.98));
}

.share-access-section__title {
  margin-bottom: 6px;
  color: #172033;
  font-size: 14px;
  font-weight: 700;
}

.share-access-section__summary {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.share-access-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.share-field-note {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 760px) {
  .security-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .share-token-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .share-limit-grid,
  .share-access-grid {
    grid-template-columns: 1fr;
  }
}
</style>
