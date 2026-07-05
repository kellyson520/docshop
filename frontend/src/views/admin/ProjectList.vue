<template>
  <div class="page-container motion-page motion-page--projects">
    <!-- 页面头部 -->
    <PageHeader
      title="项目管理"
      :breadcrumbs="breadcrumbs"
      subtitle="管理和查看所有项目"
    >
      <template #actions>
        <div class="project-header-actions">
          <el-input
            v-model="searchQuery"
            placeholder="搜索项目..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="handleSearchInput"
          />
          <el-select
            v-model="sortOrder"
            placeholder="排序方式"
            class="sort-select"
            @change="handleSortChange"
          >
            <template #prefix>
              <el-icon><Sort /></el-icon>
            </template>
            <el-option label="按时间排序" value="created_at" />
            <el-option label="按名称排序" value="name" />
            <el-option label="按文件数排序" value="file_count" />
          </el-select>
          <el-select
            v-model="tagFilter"
            placeholder="标签筛选"
            clearable
            multiple
            collapse-tags
            collapse-tags-tooltip
            size="small"
            class="tag-select"
            @change="fetchProjects"
            @visible-change="loadTagsOnOpen"
          >
            <el-option v-for="t in tagList" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
          <el-select
            v-model="categoryFilter"
            placeholder="分类筛选"
            clearable
            size="small"
            class="cat-select"
            @change="fetchProjects"
            @visible-change="loadCatsOnOpen"
          >
            <el-option v-for="c in categoryList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>
    </PageHeader>

    <!-- 批量操作栏 -->
    <div
      v-if="selectedProjects.length > 0"
      class="batch-actions-bar animate-fade-in-down"
      :class="{ 'is-busy': batchLoading }"
    >
      <div class="batch-info">
        <el-icon><Check /></el-icon>
        <div class="batch-info-text">
          <span>已选择 {{ selectedProjects.length }} 个项目</span>
          <small v-if="batchLoading">{{ batchActionText }} {{ batchProgress }}%</small>
        </div>
      </div>
      <el-progress
        v-if="batchLoading"
        class="batch-action-progress"
        :percentage="batchProgress"
        :show-text="false"
        :stroke-width="6"
      />
      <div class="batch-buttons">
        <el-button
          size="small"
          :loading="batchLoading && batchAction === 'public'"
          :disabled="batchLoading"
          @click="handleBatchPublic(true)"
        >
          <el-icon><View /></el-icon>
          批量公开
        </el-button>
        <el-button
          size="small"
          :loading="batchLoading && batchAction === 'private'"
          :disabled="batchLoading"
          @click="handleBatchPublic(false)"
        >
          <el-icon><Hide /></el-icon>
          批量私有
        </el-button>
        <el-button
          size="small"
          type="danger"
          :loading="batchLoading && batchAction === 'delete'"
          :disabled="batchLoading"
          @click="handleBatchDelete"
        >
          <el-icon><Delete /></el-icon>
          批量删除
        </el-button>
        <el-button size="small" text :disabled="batchLoading" @click="selectedProjects = []">
          取消选择
        </el-button>
      </div>
    </div>

    <SkeletonCard v-if="loading" :count="6" />

    <!-- 错误状态 -->
    <EmptyState
      v-else-if="error"
      icon="WarningFilled"
      :icon-size="64"
      icon-color="#F56C6C"
      title="加载失败"
      :description="errorMessage"
      action-text="重新加载"
      @action="handleRetry"
    />

    <!-- 项目列表 -->
    <el-row v-else :gutter="20">
      <el-col
        v-for="project in filteredProjects"
        :key="project.id"
        :xs="24"
        :sm="12"
        :lg="8"
        class="project-col"
      >
        <el-card
          shadow="hover"
          class="project-card card-hover"
          :class="{ 'is-selected': selectedProjects.includes(project.id) }"
        >
          <template #header>
            <div class="card-header">
              <el-checkbox
                :model-value="selectedProjects.includes(project.id)"
                :disabled="batchLoading"
                @change="toggleSelect(project.id)"
                @click.stop
              />
              <span class="project-name" :title="project.name">{{ project.name }}</span>
              <el-tag v-if="project.is_public" type="success" size="small">公开</el-tag>
              <el-tag v-else size="small">私有</el-tag>
            </div>
          </template>

          <p class="project-desc">{{ project.description || '暂无描述' }}</p>

          <div class="project-meta">
            <span class="meta-item">
              <el-icon><Document /></el-icon>
              {{ project.file_count || 0 }} 个文件
            </span>
            <span class="meta-item" :title="formatDate(project.created_at)">
              {{ formatRelativeTime(project.created_at) }}
            </span>
          </div>

          <div class="card-actions">
            <el-button type="primary" text @click="goToDetail(project.id)">
              <el-icon><View /></el-icon>
              查看详情
            </el-button>
            <el-button text @click="handleCopyLink(project)">
              <el-icon><Link /></el-icon>
              复制链接
            </el-button>
            <el-button type="danger" text @click="handleDelete(project)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 空状态 -->
      <el-col v-if="filteredProjects.length === 0" :span="24">
        <EmptyState
          v-if="searchQuery"
          icon="Search"
          title="未找到项目"
          description="尝试使用其他关键词搜索"
          action-text="清除搜索"
          @action="clearSearch"
        />
        <EmptyState
          v-else
          icon="FolderOpened"
          title="暂无项目"
          description="点击下方按钮创建您的第一个项目"
          action-text="新建项目"
          @action="showCreateDialog = true"
        />
      </el-col>
    </el-row>

    <!-- 分页 -->
    <div v-if="filteredProjects.length > 0 && !loading && !error" class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[9, 18, 36]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 新建项目对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建项目"
      width="480px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="rules"
        label-width="80px"
        label-position="top"
        status-icon
      >
        <el-form-item label="项目名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="请输入项目名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            placeholder="请输入项目描述"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="公开访问" prop="is_public">
          <el-switch
            v-model="createForm.is_public"
            active-text="公开"
            inactive-text="私有"
          />
          <div class="form-tip">
            公开项目可以通过分享链接被任何人访问
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          @click="handleCreate"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'ProjectList' })

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Plus,
  Search,
  View,
  Link,
  Delete,
  Document,
  Sort,
  Check,
  Hide
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { useLoading } from '@/composables/useLoading'
import { useDebounce } from '@/composables/useDebounce'
import { useConfirm } from '@/composables/useConfirm'
import { useMessage } from '@/composables/useMessage'
import {
  validateProjectName,
  validateProjectDescription,
  createRules
} from '@/utils/validators'
import { ErrorHandler } from '@/utils/error'
import { copyToClipboard, formatDate } from '@/utils'
import {
  describeBatchResult,
  getBatchFailureMessage,
  runBatchOperation
} from '@/utils/batchOperation'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import client from '@/api/client'
import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'
import { buildShareAbsoluteUrl } from '@/utils/shareRoute'

// ==================== 路由和状态 ====================
const router = useRouter()
const projectStore = useProjectStore()
const { confirmDelete } = useConfirm()
const { success, error: showError, warning } = useMessage()

// ==================== 面包屑导航 ====================
const breadcrumbs = [
  { title: '项目管理' }
]

// ==================== 响应式数据 ====================
const searchQuery = ref('')
const sortOrder = ref('created_at')
const tagFilter = ref([])
const categoryFilter = ref('')
const tagList = ref([])
const categoryList = ref([])
const currentPage = ref(1)
const pageSize = ref(9)
const total = ref(0)
const showCreateDialog = ref(false)
const createFormRef = ref(null)
const error = ref(false)
const errorMessage = ref('')
const selectedProjects = ref([])
const batchLoading = ref(false)
const batchAction = ref('')
const batchProgress = ref(0)

// 创建表单
const createForm = ref({
  name: '',
  description: '',
  is_public: false
})

// 搜索防抖
const { debouncedFn: debouncedSearch, cancel: cancelSearch } = useDebounce(() => {
  currentPage.value = 1
  fetchProjects()
}, 300)

// ==================== 加载状态 ====================
const { loading, start: startLoading, stop: stopLoading } = useLoading()
const {
  loading: creating,
  start: startCreating,
  stop: stopCreating
} = useLoading()

// ==================== 计算属性 ====================

/**
 * 过滤并排序后的项目列表
 */
const filteredProjects = computed(() => {
  let result = [...projectStore.projects]

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase().trim()
    result = result.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        (p.description || '').toLowerCase().includes(query)
    )
  }

  // 排序
  result.sort((a, b) => {
    switch (sortOrder.value) {
      case 'name':
        return a.name.localeCompare(b.name, 'zh-CN')
      case 'file_count':
        return (b.file_count || 0) - (a.file_count || 0)
      case 'created_at':
      default:
        return new Date(b.created_at) - new Date(a.created_at)
    }
  })

  return result
})

// ==================== 表单校验规则 ====================
const rules = {
  name: createRules(validateProjectName),
  description: createRules(validateProjectDescription)
}

const batchActionText = computed(() => {
  const labels = {
    public: '正在公开',
    private: '正在设为私有',
    delete: '正在删除'
  }
  return labels[batchAction.value] || '正在处理'
})

// ==================== 生命周期 ====================
onMounted(() => {
  fetchProjects()
})

// ==================== 方法 ====================

/**
 * 获取项目列表
 */
async function fetchProjects() {
  error.value = false
  errorMessage.value = ''
  startLoading('加载项目中...')

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: searchQuery.value || undefined,
    }
    const data = await projectStore.fetchProjects(params)
    total.value = data.total || projectStore.projects.length
  } catch (err) {
    error.value = true
    errorMessage.value = '无法加载项目列表，请检查网络连接'
    ErrorHandler.handle(err, { silent: true })
  } finally {
    stopLoading()
  }
}

/**
 * 搜索输入处理（防抖）
 */
function handleSearchInput() {
  debouncedSearch()
}

function loadTagsOnOpen(visible) {
  if (visible && tagList.value.length === 0) {
    client.get('/tags').then(d => { tagList.value = d || [] }).catch(() => {})
  }
}

function loadCatsOnOpen(visible) {
  if (visible && categoryList.value.length === 0) {
    client.get('/categories').then(d => { categoryList.value = d || [] }).catch(() => {})
  }
}

/**
 * 排序方式变化处理
 */
function handleSortChange() {
  currentPage.value = 1
}

/**
 * 清除搜索
 */
function clearSearch() {
  searchQuery.value = ''
  currentPage.value = 1
}

/**
 * 重试加载
 */
function handleRetry() {
  fetchProjects()
}

/**
 * 跳转到项目详情
 * @param {number} id - 项目ID
 */
function goToDetail(id) {
  router.push(`/admin/projects/${id}`)
}

/**
 * 切换项目选中状态
 * @param {number} id - 项目ID
 */
function toggleSelect(id) {
  const index = selectedProjects.value.indexOf(id)
  if (index > -1) {
    selectedProjects.value.splice(index, 1)
  } else {
    selectedProjects.value.push(id)
  }
}

/**
 * 批量公开/私有
 * @param {boolean} isPublic - 是否公开
 */
function isDialogCancel(err) {
  return err === 'cancel' || err === 'close'
}

function startBatchAction(action) {
  batchLoading.value = true
  batchAction.value = action
  batchProgress.value = 0
}

function stopBatchAction() {
  batchLoading.value = false
  batchAction.value = ''
  batchProgress.value = 0
}

function updateBatchProgress(event) {
  batchProgress.value = event.percent
}

function showBatchResult(result, options) {
  const summary = describeBatchResult(result, options)

  if (result.ok) {
    success(summary.message)
    selectedProjects.value = []
    return
  }

  selectedProjects.value = result.failures.map((failure) => failure.item)
  const detail = getBatchFailureMessage(result, summary.message)

  if (result.partial) {
    warning(`${summary.message}；${detail}`)
  } else {
    showError(detail)
  }
}

/**
 * 批量公开/私有
 * @param {boolean} isPublic - 是否公开
 */
async function handleBatchPublic(isPublic) {
  if (batchLoading.value) return

  const ids = [...selectedProjects.value]
  if (ids.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要将 ${ids.length} 个项目设为${isPublic ? '公开' : '私有'}吗？`,
      '批量设置',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )

    startBatchAction(isPublic ? 'public' : 'private')
    const result = await runBatchOperation(
      ids,
      (id) => projectStore.updateProject(id, { is_public: isPublic }),
      { onProgress: updateBatchProgress }
    )

    showBatchResult(result, {
      successVerb: isPublic ? '已公开' : '已设为私有',
      failureVerb: isPublic ? '公开失败' : '设为私有失败',
      unit: '个项目'
    })
    await fetchProjects()
  } catch (err) {
    if (!isDialogCancel(err)) {
      ErrorHandler.handle(err, {
        fallbackMessage: '批量设置失败，请稍后重试'
      })
    }
  } finally {
    stopBatchAction()
  }
}

/**
 * 批量删除
 */
async function handleBatchDelete() {
  if (batchLoading.value) return

  const ids = [...selectedProjects.value]
  if (ids.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${ids.length} 个项目吗？此操作不可撤销。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )

    startBatchAction('delete')
    const result = await runBatchOperation(
      ids,
      (id) => projectStore.deleteProject(id),
      { onProgress: updateBatchProgress }
    )

    showBatchResult(result, {
      successVerb: '已删除',
      failureVerb: '删除失败',
      unit: '个项目'
    })
    await fetchProjects()
  } catch (err) {
    if (!isDialogCancel(err)) {
      ErrorHandler.handle(err, {
        fallbackMessage: '批量删除失败，请稍后重试'
      })
    }
  } finally {
    stopBatchAction()
  }
}

/**
 * 复制分享链接
 * @param {Object} project - 项目对象
 */
async function handleCopyLink(project) {
  const link = buildShareAbsoluteUrl(project?.share_token, window.location.origin)
  if (!link) {
    showError('分享令牌缺失，无法复制链接')
    return
  }
  const successCopied = await copyToClipboard(link)
  if (successCopied) {
    success('分享链接已复制到剪贴板')
  } else {
    showError('复制失败，请手动复制')
  }
}

/**
 * 删除项目
 * @param {Object} project - 项目对象
 */
async function handleDelete(project) {
  try {
    await confirmDelete({
      title: '删除项目',
      message: `确定要删除项目「${project.name}」吗？此操作不可撤销，项目下的所有文件也将被删除。`
    })

    startLoading('删除中...')
    await projectStore.deleteProject(project.id)
    success('项目已删除')
  } catch (err) {
    // 用户取消或删除失败
    if (err !== 'cancel') {
      ErrorHandler.handle(err, {
        fallbackMessage: '删除失败，请稍后重试'
      })
    }
  } finally {
    stopLoading()
  }
}

/**
 * 创建项目
 */
async function handleCreate() {
  if (!createFormRef.value) return

  try {
    await createFormRef.value.validate()
  } catch {
    return
  }

  startCreating()

  try {
    await projectStore.createProject(createForm.value)
    success('项目创建成功')
    showCreateDialog.value = false
    // 重置表单
    createForm.value = { name: '', description: '', is_public: false }
    // 刷新列表
    await fetchProjects()
  } catch (err) {
    ErrorHandler.handle(err, {
      fallbackMessage: '创建失败，请稍后重试'
    })
  } finally {
    stopCreating()
  }
}

/**
 * 处理分页大小变化
 * @param {number} size - 每页条数
 */
function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchProjects()
}

/**
 * 处理页码变化
 * @param {number} page - 当前页码
 */
function handlePageChange(page) {
  currentPage.value = page
  fetchProjects()
}

/**
 * 格式化相对时间
 * @param {string} isoString - ISO 格式日期
 * @returns {string} 相对时间描述
 */
function formatRelativeTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day

  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)} 分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} 小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)} 天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)} 周前`
  } else {
    return formatDate(isoString)
  }
}
</script>

<style scoped>
/* 搜索和排序区域 */
.project-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.search-input {
  width: 200px;
}

.sort-select {
  width: 150px;
}
.tag-select { width: 180px; }
.cat-select { width: 130px; }

/* 批量操作栏 */
.batch-actions-bar {
  display: grid;
  grid-template-columns: auto minmax(120px, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #ecf5ff, #f0f9ff);
  border: 1px solid #b3d8fd;
  border-radius: 8px;
  margin-bottom: 20px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.batch-actions-bar.is-busy {
  border-color: var(--color-primary, #1A5276);
  box-shadow: 0 10px 24px rgba(26, 82, 118, 0.12);
}

[data-theme="dark"] .batch-actions-bar {
  background: linear-gradient(135deg, #1a3a5c, #1a2a4c);
  border-color: #3a6a9c;
}

.batch-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary, #1A5276);
}

.batch-info-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.batch-info-text small {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary, #475569);
}

.batch-action-progress {
  min-width: 120px;
}

[data-theme="dark"] .batch-info {
  color: #8cc8f0;
}

.batch-buttons {
  display: flex;
  gap: 8px;
}

.project-col {
  margin-bottom: 20px;
}

.project-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.project-card.is-selected {
  border-color: var(--color-primary, #1A5276);
  box-shadow: 0 0 0 2px rgba(26, 82, 118, 0.2);
}

[data-theme="dark"] .project-card.is-selected {
  border-color: var(--color-primary, #4A9BD9);
  box-shadow: 0 0 0 2px rgba(74, 155, 217, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header .el-checkbox {
  flex-shrink: 0;
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #172033);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.project-desc {
  color: var(--text-secondary, #475569);
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 44px;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  color: var(--text-tertiary, #7a8798);
  font-size: 13px;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  border-top: 1px solid var(--border-color-light, #e4e9f0);
  padding-top: 12px;
  margin-top: auto;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color-light, #e4e9f0);
}

.form-tip {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
  margin-top: 4px;
  line-height: 1.4;
}

/* 响应式适配 */
@media (max-width: 767px) {
  .project-header-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .project-header-actions .search-input,
  .project-header-actions .tag-select,
  .project-header-actions :deep(.el-button) {
    grid-column: 1 / -1;
  }

  .search-input {
    width: 100%;
  }

  .sort-select {
    width: 100%;
  }
  .tag-select, .cat-select { width: 100%; }

  .batch-actions-bar {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 12px;
    padding: 12px;
    margin-bottom: 12px;
  }

  .batch-buttons {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .batch-buttons :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  .batch-buttons :deep(.el-button:last-child) {
    grid-column: 1 / -1;
  }

  .project-col {
    margin-bottom: 12px;
  }

  .card-header {
    gap: 8px;
  }

  .project-name {
    font-size: 15px;
  }

  .project-desc {
    min-height: auto;
    margin-bottom: 12px;
    -webkit-line-clamp: 2;
  }

  .project-meta {
    flex-wrap: wrap;
    gap: 8px 12px;
    margin-bottom: 12px;
  }

  .card-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    padding-top: 10px;
  }

  .card-actions :deep(.el-button) {
    width: 100%;
    min-height: 36px;
    padding: 0 6px;
    margin-left: 0;
  }

  .pagination-container {
    justify-content: center;
    margin-top: 12px;
    padding-top: 12px;
  }
}

@media (max-width: 380px) {
  .project-header-actions {
    grid-template-columns: 1fr;
  }

  .card-actions {
    grid-template-columns: 1fr;
  }
}
</style>
