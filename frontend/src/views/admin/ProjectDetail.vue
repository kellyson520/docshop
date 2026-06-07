<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <PageHeader
      title="项目详情"
      :breadcrumbs="breadcrumbs"
      :subtitle="project?.name"
    >
      <template #actions>
        <el-button @click="router.push('/admin/projects')">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
      </template>
    </PageHeader>

    <!-- 项目信息卡片 -->
    <el-card v-loading="loading" shadow="never" class="project-info-card mb-4">
      <div class="project-info">
        <div class="info-left">
          <h2>{{ project?.name }}</h2>
          <p class="project-desc">{{ project?.description || '暂无描述' }}</p>
          <div class="project-meta">
            <el-tag v-if="project?.is_public" type="success" size="small">公开</el-tag>
            <el-tag v-else size="small">私有</el-tag>
            <span class="meta-divider">|</span>
            <span>创建于 {{ formatDate(project?.created_at) }}</span>
            <span class="meta-divider">|</span>
            <span>{{ files.length }} 个文件</span>
          </div>
        </div>
        <div class="info-right">
          <div class="share-section">
            <span class="share-label">分享链接:</span>
            <div class="share-input-group">
              <el-input
                :model-value="shareLink"
                readonly
                size="small"
                class="share-input"
              >
                <template #append>
                  <el-button
                    :icon="copyIcon"
                    @click="handleCopyLink"
                    class="copy-btn"
                  >
                    {{ copied ? '已复制' : '复制' }}
                  </el-button>
                </template>
              </el-input>
            </div>
          </div>
          <el-button type="primary" @click="goToUpload" class="btn-hover-lift">
            <el-icon><Upload /></el-icon>
            上传文件
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 文件列表卡片 -->
    <el-card shadow="never" class="file-list-card">
      <template #header>
        <div class="card-header">
          <span>文件列表</span>
          <el-tag type="info">共 {{ files.length }} 个文件</el-tag>
        </div>
      </template>

      <div class="file-list-toolbar">
        <el-input
          v-model="fileSearchQuery"
          placeholder="搜索文件..."
          :prefix-icon="Search"
          clearable
          size="small"
          class="file-search-input"
        />
        <el-select
          v-model="fileTypeFilter"
          placeholder="文件类型"
          clearable
          size="small"
          class="file-type-filter"
        >
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="docx" />
          <el-option label="Excel" value="xlsx" />
        </el-select>
        <el-select
          v-model="fileTagFilter"
          placeholder="标签"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          size="small"
          class="file-tag-filter"
          @visible-change="onTagFilterOpen"
        >
          <el-option v-for="t in fileTagList" :key="t.id" :label="t.name" :value="t.id">
            <span class="tag-dot" :style="{background:t.color}"></span>
            {{ t.name }}
          </el-option>
        </el-select>
        <el-select
          v-model="fileCategoryFilter"
          placeholder="分类"
          clearable
          size="small"
          class="file-cat-filter"
          @visible-change="onCatFilterOpen"
        >
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>

      <el-table
        :data="filteredFiles"
        stripe
        style="width: 100%"
        row-key="id"
        :row-class-name="tableRowClassName"
        @expand-change="onExpandChange"
        class="file-table"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="version-expand" v-loading="row._loadingVersions">
              <div class="version-expand-header">
                <span class="ve-title">版本列表 - {{ row.original_filename }}</span>
              </div>
              <div v-if="row._versions && row._versions.length" class="version-list">
                <div
                  v-for="(v, vi) in row._versions"
                  :key="v.id"
                  class="version-row"
                  :class="{ 'version-row-latest': vi === 0 }"
                >
                  <span class="vr-num">V{{ v.version }}</span>
                  <span class="vr-hash">{{ v.file_hash?.slice(0, 8) || '-' }}</span>
                  <span class="vr-size">{{ formatFileSize(v.file_size) }}</span>
                  <span class="vr-time">{{ formatDate(v.created_at) }}</span>
                  <span class="vr-actions">
                    <el-button text size="small" @click="moveVersion(row, v, -1)" :disabled="vi === 0">
                      <el-icon><ArrowUp /></el-icon>
                    </el-button>
                    <el-button text size="small" @click="moveVersion(row, v, 1)" :disabled="vi === row._versions.length - 1">
                      <el-icon><ArrowDown /></el-icon>
                    </el-button>
                    <el-button text size="small" type="danger" @click="deleteVersion(row, v)" :disabled="row._versions.length <= 1">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </span>
                </div>
              </div>
              <el-empty v-else description="暂无版本" :image-size="40" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :size="20" :class="getFileTypeColor(row.file_type)">
                <component :is="getFileTypeIcon(row.file_type)" />
              </el-icon>
              <div class="file-info">
                <span class="file-name">{{ row.original_filename }}</span>
                <span class="file-path">文件 ID：{{ shortFileId(row.id) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getFileTypeTagType(row.file_type)">
              {{ row.file_type?.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前版本" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">v{{ row.current_version || 1 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" width="120">
          <template #default="{ row }">
            <span class="file-size">{{ formatFileSize(row.file_size) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            <span class="file-time">{{ formatDate(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="460" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button text type="primary" size="small" @click.stop="handlePreview(row)">
                <el-icon><View /></el-icon>
                预览
              </el-button>
              <el-button text size="small" @click.stop="openVersionManage(row)">
                <el-icon><Edit /></el-icon>
                版本
              </el-button>
              <el-button text size="small" @click.stop="openFileEditDialog(row)">
                <el-icon><PriceTag /></el-icon>
                设置
              </el-button>
              <el-button text type="primary" size="small" @click.stop="goToDiff(row.id)">
                <el-icon><Sort /></el-icon>
                Diff
              </el-button>
              <el-button text type="success" size="small" @click.stop="goToUploadVersion(row.id)">
                <el-icon><Upload /></el-icon>
                新版本
              </el-button>
              <el-button text type="danger" size="small" @click.stop="handleDeleteFile(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && filteredFiles.length === 0" description="暂无文件，点击上方按钮上传">
        <el-button type="primary" @click="goToUpload">上传文件</el-button>
      </el-empty>
    </el-card>

    <!-- 文件预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="previewFile?.original_filename"
      width="min(1280px, calc(100vw - 64px))"
      top="5vh"
      destroy-on-close
      append-to-body
      modal-class="preview-dialog-mask"
      class="preview-dialog"
      @closed="onPreviewDialogClosed"
    >
      <div class="preview-container">
        <div v-if="previewLoading" class="preview-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载预览中...</span>
        </div>
        <div v-else-if="previewError" class="preview-error">
          <el-icon :size="48"><WarningFilled /></el-icon>
          <p>{{ previewError }}</p>
          <el-button type="primary" @click="loadPreview">重试</el-button>
        </div>
        <div v-else class="preview-content">
          <div class="preview-header">
            <span>版本: v{{ previewVersion }}</span>
            <el-select v-model="previewVersion" size="small" @change="loadPreview">
              <el-option
                v-for="v in fileVersions"
                :key="v"
                :label="`版本 ${v}`"
                :value="v"
              />
            </el-select>
          </div>
          <div class="preview-body">
            <div v-if="previewUrl" class="preview-iframe-container">
              <iframe :src="previewUrl" class="preview-iframe"></iframe>
            </div>
            <div v-else class="preview-placeholder">
              <el-icon :size="64"><Document /></el-icon>
              <p>文档预览</p>
              <el-button type="primary" @click="downloadFile(previewFile)">
                <el-icon><Download /></el-icon>
                下载查看
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 版本管理对话框 -->
    <el-dialog
      v-model="versionTimelineVisible"
      :title="'版本管理 - ' + (manageFile?.original_filename || '')"
      width="680px"
      destroy-on-close
      @opened="fetchRealVersions"
    >
      <div v-loading="categoryLoading" class="version-manage">
        <div v-if="realVersions.length" class="vm-list">
          <div v-for="(v, vi) in realVersions" :key="v.id" class="vm-row" :class="{ 'vm-latest': vi === 0 }">
            <span class="vm-num"><strong>V{{ v.version }}</strong></span>
            <span class="vm-meta">{{ formatFileSize(v.file_size) }} · {{ v.file_hash?.slice(0,8) || '-' }}</span>
            <span class="vm-time">{{ formatDate(v.created_at) }}</span>
            <span class="vm-actions">
              <el-button size="small" text @click="moveVersionApi(vi, -1)" :disabled="vi === 0"><el-icon><ArrowUp /></el-icon></el-button>
              <el-button size="small" text @click="moveVersionApi(vi, 1)" :disabled="vi === realVersions.length - 1"><el-icon><ArrowDown /></el-icon></el-button>
              <el-button size="small" text type="danger" @click="deleteVersionApi(vi)" :disabled="realVersions.length <= 1"><el-icon><Delete /></el-icon></el-button>
            </span>
          </div>
        </div>
        <el-empty v-else description="暂无版本" />
      </div>
      <template #footer>
        <el-button @click="versionTimelineVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 分类标签对话框 -->
    <el-dialog
      v-model="categoryDialogVisible"
      title="分类与标签"
      width="500px"
      destroy-on-close
    >
      <div class="cat-tag-form">
        <div class="ct-item">
          <span class="ct-label">分类：</span>
          <el-select v-model="selectedCategoryId" placeholder="选择分类" clearable style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id">
              <span :style="{display:'inline-block',width:'10px',height:'10px',borderRadius:'50%',background:c.color,marginRight:'6px'}"></span>
              {{ c.name }}
            </el-option>
          </el-select>
        </div>
        <div class="ct-item">
          <span class="ct-label">标签：</span>
          <el-select v-model="selectedTagIds" multiple placeholder="选择标签" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id">
              <span :style="{display:'inline-block',width:'8px',height:'8px',borderRadius:'2px',background:t.color,marginRight:'6px'}"></span>
              {{ t.name }}
            </el-option>
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="fetchCategoriesTags">刷新</el-button>
        <el-button type="primary" @click="saveCategoryTags">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文件设置对话框 -->
    <el-dialog
      v-model="fileEditVisible"
      title="文件设置"
      width="560px"
      destroy-on-close
      @opened="loadFileEditData"
    >
      <el-form label-position="top" class="file-edit-form">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" placeholder="可选，不填则使用原文件名" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="文档描述..." />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category_id" placeholder="选择分类" clearable style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id">
              <span :style="{display:'inline-block',width:'10px',height:'10px',borderRadius:'50%',background:c.color,marginRight:'6px'}"></span>
              {{ c.name }}
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="editForm.tag_ids" multiple placeholder="选择标签" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id">
              <span :style="{display:'inline-block',width:'8px',height:'8px',borderRadius:'2px',background:t.color,marginRight:'6px'}"></span>
              {{ t.name }}
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="封面图片">
          <div v-if="editForm.cover_image" class="cover-preview">
            <img :src="editForm.cover_image" alt="封面" style="max-height:120px;border-radius:8px" />
            <el-button size="small" type="danger" text @click="editForm.cover_image = ''">移除封面</el-button>
          </div>
          <el-upload
            v-else
            :show-file-list="false"
            :before-upload="handleCoverUpload"
            accept="image/*"
          >
            <el-button size="small">
              <el-icon><Upload /></el-icon> 上传封面
            </el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="loadCategories">刷新分类标签</el-button>
        <el-button type="primary" @click="saveFileEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ArrowUp, ArrowDown, Upload, Search, View, Sort, Delete,
  CopyDocument, Document, DocumentCopy, Grid, Download, WarningFilled,
  Loading, Check, Edit, Top, Bottom, Plus, Minus, PriceTag, Folder
} from '@element-plus/icons-vue'
import { getProject } from '@/api/project'
import { deleteFile } from '@/api/file'
import client from '@/api/client'
import { resolveCoverUrl } from '@/utils/cover'
import { formatDate, formatFileSize, getFileTypeIcon, copyToClipboard } from '@/utils'
import PageHeader from '@/components/common/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const project = ref(null)
const files = ref([])
const loading = ref(false)
const fileSearchQuery = ref('')
const fileTypeFilter = ref('')
const fileTagFilter = ref([])
const fileCategoryFilter = ref('')
const fileTagList = ref([])
const copied = ref(false)
const copyIcon = computed(() => copied.value ? Check : CopyDocument)

// 预览相关
const previewDialogVisible = ref(false)
const previewFile = ref(null)
const previewUrl = ref('')
const previewLoading = ref(false)
const previewError = ref('')
const previewVersion = ref(1)
const fileVersions = ref([])
const versionTimelineVisible = ref(false)
const manageFile = ref(null)
const realVersions = ref([])
const categories = ref([])
const tags = ref([])
const selectedCategoryId = ref(null)
const selectedTagIds = ref([])
const categoryLoading = ref(false)
const expandedRows = ref([])

const breadcrumbs = computed(() => [
  { title: '项目管理', path: '/admin/projects' },
  { title: project.value?.name || '项目详情' }
])

const shareLink = computed(() => {
  if (project.value?.share_token) {
    return `${window.location.origin}/s/${project.value.share_token}`
  }
  return ''
})

const filteredFiles = computed(() => {
  let result = files.value
  if (fileSearchQuery.value) {
    const query = fileSearchQuery.value.toLowerCase()
    result = result.filter(f =>
      f.original_filename.toLowerCase().includes(query) ||
      (f.display_name || '').toLowerCase().includes(query) ||
      (f.id || '').toLowerCase().includes(query)
    )
  }
  if (fileTypeFilter.value) {
    result = result.filter(f => f.file_type === fileTypeFilter.value)
  }
  if (fileTagFilter.value.length) {
    result = result.filter(f => {
      const fileTagIds = (f.tags || []).map(t => t.id || t)
      return fileTagFilter.value.some(tid => fileTagIds.includes(tid))
    })
  }
  if (fileCategoryFilter.value) {
    result = result.filter(f => f.category_id === fileCategoryFilter.value)
  }
  return result
})

function onTagFilterOpen(visible) {
  if (visible && fileTagList.value.length === 0) {
    client.get('/tags').then(d => { fileTagList.value = d || [] }).catch(() => {})
  }
}

function onCatFilterOpen(visible) {
  if (visible && categories.value.length === 0) {
    client.get('/categories').then(d => { categories.value = d || [] }).catch(() => {})
  }
}

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function getFileTypeColor(type) {
  const map = { pdf: 'file-icon-pdf', docx: 'file-icon-docx', doc: 'file-icon-docx', xlsx: 'file-icon-xlsx', xls: 'file-icon-xlsx' }
  return map[type] || 'file-icon-default'
}

function shortFileId(id) {
  return id ? String(id).slice(0, 8).toUpperCase() : '-'
}

function tableRowClassName({ rowIndex }) {
  if (rowIndex % 2 === 0) return 'even-row'
  return 'odd-row'
}

function handleRowClick(row) {
  handlePreview(row)
}

async function handleCopyLink() {
  const success = await copyToClipboard(shareLink.value)
  if (success) {
    copied.value = true
    ElMessage.success('分享链接已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
}

function goToUpload() {
  router.push(`/admin/projects/${route.params.id}/upload`)
}

function goToUploadVersion(fileId) {
  router.push({ path: `/admin/projects/${route.params.id}/upload`, query: { fileId } })
}

function goToDiff(fileId) {
  router.push(`/admin/projects/${route.params.id}/diff/${fileId}`)
}

async function handleDeleteFile(file) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件「${file.original_filename}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await deleteFile(file.id)
    files.value = files.value.filter((f) => f.id !== file.id)
    ElMessage.success('文件已删除')
  } catch {
    // 用户取消
  }
}

function handlePreview(file) {
  // 清理旧的 blob URL
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  previewFile.value = file
  previewVersion.value = file.current_version || 1
  fileVersions.value = generateVersions(file.current_version || 1)
  previewDialogVisible.value = true
  loadPreview()
}

function generateVersions(currentVersion) {
  const versions = []
  for (let i = currentVersion; i >= 1; i--) {
    versions.push(i)
  }
  return versions
}

async function loadPreview() {
  if (!previewFile.value) return
  previewLoading.value = true
  previewError.value = ''

  // 清理旧的 blob URL
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }

  try {
    const url = `/files/${previewFile.value.id}/preview`
    const blob = await client.get(url, {
      params: { version: previewVersion.value },
      responseType: 'blob',
      timeout: 120000
    })
    // responseType: 'blob' 时，axios 拦截器会直接返回 Blob 对象。
    // 检查 blob 是否为 JSON 错误响应
    if (blob.type && blob.type.includes('application/json')) {
      const text = await blob.text()
      try {
        const errData = JSON.parse(text)
        throw new Error(errData.message || errData.detail || '预览失败')
      } catch (e) {
        if (e.message && e.message !== '预览失败') throw e
        throw new Error('预览失败：服务器返回了错误响应')
      }
    }

    previewUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    previewError.value = err.message || '预览加载失败，请重试'
    previewUrl.value = ''
  } finally {
    previewLoading.value = false
  }
}

function handlePreviewVersion(version) {
  previewVersion.value = version
  loadPreview()
}

async function downloadFile(file) {
  if (!file) return
  try {
    const blob = await client.get(`/files/${file.id}/download`, {
      params: { version: previewVersion.value },
      responseType: 'blob',
      timeout: 120000
    })
    const objectUrl = URL.createObjectURL(blob)
    window.open(objectUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
  } catch (err) {
    ElMessage.error(err.message || '文件下载失败')
  }
}

function onPreviewDialogClosed() {
  // 清理 blob URL 释放内存
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = ''
  previewFile.value = null
  previewLoading.value = false
  previewError.value = ''
}

function getVersionTime(version) {
  // 模拟版本时间
  const baseTime = new Date(previewFile.value?.updated_at || Date.now())
  const diffDays = (previewFile.value?.current_version || 1) - version
  const time = new Date(baseTime.getTime() - diffDays * 24 * 60 * 60 * 1000)
  return formatDate(time.toISOString())
}

function getVersionChangelog(version) {
  return previewFile.value?.changelog || ''
}

const categoryDialogVisible = ref(false)
const fileEditVisible = ref(false)
const editForm = ref({ display_name: '', description: '', category_id: null, tag_ids: [], cover_image: '' })

function onExpandChange(row, expandedRowsList) {
  if (expandedRowsList.includes(row)) {
    fetchVersionsForRow(row)
  }
}

async function fetchVersionsForRow(row) {
  row._loadingVersions = true
  try {
    const data = await client.get(`/files/${row.id}/versions`)
    const items = data.versions || data || []
    row._versions = Array.isArray(items) ? items : []
  } catch {
    row._versions = []
  } finally {
    row._loadingVersions = false
  }
}

// 版本管理
function openVersionManage(file) {
  manageFile.value = file
  versionTimelineVisible.value = true
}

async function fetchRealVersions() {
  if (!manageFile.value) return
  categoryLoading.value = true
  try {
    const data = await client.get(`/files/${manageFile.value.id}/versions`)
    const items = data.versions || data || []
    realVersions.value = Array.isArray(items) ? items : []
  } catch {
    realVersions.value = []
  } finally {
    categoryLoading.value = false
  }
}

async function moveVersionApi(fromIdx, direction) {
  const arr = [...realVersions.value]
  const toIdx = fromIdx + direction
  if (toIdx < 0 || toIdx >= arr.length) return
  ;[arr[fromIdx], arr[toIdx]] = [arr[toIdx], arr[fromIdx]]
  const orderedIds = arr.map(v => v.id)
  try {
    await client.put(`/files/${manageFile.value.id}/versions/reorder`, orderedIds)
    await fetchRealVersions()
    ElMessage.success('排序已更新')
  } catch {
    ElMessage.error('排序失败')
  }
}

async function deleteVersionApi(idx) {
  const v = realVersions.value[idx]
  try {
    await ElMessageBox.confirm(`确定删除 V${v.version}？剩余版本会自动重编号。`, '删除版本', { type: 'warning' })
    await client.delete(`/files/${manageFile.value.id}/versions/${v.id}`)
    await fetchRealVersions()
    ElMessage.success('已删除并重排版本')
  } catch { /* 取消 */ }
}

async function moveVersion(row, v, direction) {
  const arr = [...row._versions]
  const idx = arr.findIndex(x => x.id === v.id)
  if (idx < 0) return
  const toIdx = idx + direction
  if (toIdx < 0 || toIdx >= arr.length) return
  ;[arr[idx], arr[toIdx]] = [arr[toIdx], arr[idx]]
  try {
    await client.put(`/files/${row.id}/versions/reorder`, arr.map(x => x.id))
    row._versions = arr
    ElMessage.success('已调整')
  } catch {
    ElMessage.error('调整失败')
  }
}

async function deleteVersion(row, v) {
  try {
    await ElMessageBox.confirm(`删除 V${v.version}？`, '确认', { type: 'warning' })
    await client.delete(`/files/${row.id}/versions/${v.id}`)
    row._versions = row._versions.filter(x => x.id !== v.id)
    // 重编号本地显示
    row._versions.forEach((vv, i) => { vv.version = i + 1 })
    ElMessage.success('已删除')
  } catch { /* 取消 */ }
}

// 文件设置编辑
async function loadCategories() {
  try {
    const [catRes, tagRes] = await Promise.all([client.get('/categories'), client.get('/tags')])
    categories.value = catRes || []
    tags.value = tagRes || []
  } catch { /* ignore */ }
}

async function loadFileEditData() {
  if (!manageFile.value) return
  await loadCategories()
  try {
    const data = await client.get(`/files/${manageFile.value.id}`)
    editForm.value = {
      display_name: data.display_name || '',
      description: data.description || '',
      category_id: data.category_id || null,
      tag_ids: (data.tags || []).map(t => t.id || t),
      cover_image: resolveCoverUrl(data.cover_image) || '',
    }
  } catch {
    editForm.value = { display_name: '', description: '', category_id: null, tag_ids: [], cover_image: '' }
  }
}

function openFileEditDialog(file) {
  manageFile.value = file
  fileEditVisible.value = true
}

async function saveFileEdit() {
  if (!manageFile.value) return
  try {
    const fid = manageFile.value.id
    await client.put(`/cards/${fid}/info`, {
      display_name: editForm.value.display_name,
      description: editForm.value.description,
    })
    await client.put(`/files/${fid}/version/${fid}/category-tags`, {
      category_id: editForm.value.category_id || null,
      tag_ids: editForm.value.tag_ids || [],
    })
    ElMessage.success('设置已保存')
    fileEditVisible.value = false
    fetchProjectData()
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.message || '未知错误'))
  }
}

async function handleCoverUpload(file) {
  try {
    const form = new FormData()
    form.append('cover', file)
    const data = await client.post(`/cards/${manageFile.value.id}/cover`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    editForm.value.cover_image = resolveCoverUrl(data.cover_image || data.cover_url || data.relative_path)
    ElMessage.success('封面上传成功')
  } catch {
    ElMessage.error('封面上传失败')
  }
  return false // 阻止默认上传
}

async function fetchProjectData() {
  loading.value = true
  try {
    const data = await getProject(route.params.id)
    project.value = data
    files.value = data.files || []
  } catch (err) {
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProjectData()
})
</script>

<style scoped>
.project-info-card {
  border-radius: 12px;
}

.project-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.info-left {
  flex: 1;
}

.project-info h2 {
  font-size: 22px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.project-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  font-size: 13px;
}

.meta-divider {
  color: #ddd;
}

.info-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.share-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.share-label {
  color: #666;
  font-size: 13px;
  white-space: nowrap;
}

.share-input {
  width: 320px;
}

.copy-btn {
  min-width: 60px;
}

.file-list-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.file-list-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.file-search-input {
  width: 200px;
}
.file-type-filter { width: 110px; }
.file-tag-filter { width: 180px; }
.file-cat-filter { width: 130px; }
.tag-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }

.file-table {
  cursor: pointer;
}

.file-table :deep(.el-table__row) {
  transition: background-color 0.15s ease;
}

.file-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.file-table :deep(.even-row) {
  background-color: #fafafa;
}

.file-table :deep(.odd-row) {
  background-color: #ffffff;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon-pdf { color: #E74C3C; }
.file-icon-docx { color: #2980b9; }
.file-icon-xlsx { color: #27AE60; }
.file-icon-default { color: #909399; }

.file-info {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  color: #333;
}

.file-path {
  font-size: 12px;
  color: #999;
}

.file-size, .file-time {
  font-size: 13px;
  color: #666;
}

.action-buttons {
  display: inline-flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}

/* 版本展开行 */
.version-expand { padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e5e7eb; }
.version-expand-header { margin-bottom: 10px; }
.ve-title { font-weight: 600; font-size: 13px; color: #374151; }
.version-list { display: flex; flex-direction: column; gap: 4px; }
.version-row { display: flex; align-items: center; gap: 12px; padding: 6px 12px; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 12px; }
.version-row-latest { border-left: 3px solid #22c55e; }
.vr-num { font-weight: 700; color: #6366f1; min-width: 32px; }
.vr-hash { color: #9ca3af; font-family: monospace; font-size: 11px; min-width: 70px; }
.vr-size { color: #6b7280; min-width: 60px; }
.vr-time { color: #9ca3af; flex: 1; }
.vr-actions { display: flex; gap: 2px; }

/* 版本管理对话框 */
.version-manage { min-height: 200px; }
.vm-list { display: flex; flex-direction: column; gap: 6px; }
.vm-row { display: flex; align-items: center; gap: 12px; padding: 8px 14px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }
.vm-latest { border-left: 3px solid #22c55e; background: #f0fdf4; }
.vm-num { min-width: 44px; }
.vm-meta { color: #6b7280; font-size: 12px; flex: 1; }
.vm-time { color: #9ca3af; font-size: 12px; }
.vm-actions { display: flex; gap: 4px; }

/* 分类标签 */
.cat-tag-form { display: flex; flex-direction: column; gap: 16px; }
.ct-item { display: flex; flex-direction: column; gap: 4px; }
.ct-label { font-size: 13px; font-weight: 600; color: #374151; }

/* 文件设置 */
.file-edit-form .el-form-item { margin-bottom: 14px; }
.cover-preview { display: flex; align-items: center; gap: 12px; }

/* 预览对话框 */
:global(.preview-dialog-mask) {
  z-index: 3000 !important;
}

:global(.preview-dialog) {
  z-index: 3001 !important;
  max-width: calc(100vw - 64px);
}

:global(.preview-dialog .el-dialog__body) {
  padding: 16px !important;
}

.preview-container {
  height: 70vh;
  display: flex;
  flex-direction: column;
}

.preview-loading, .preview-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #666;
}

.preview-error {
  color: #E74C3C;
}

.preview-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.preview-body {
  flex: 1;
  overflow: hidden;
}

.preview-iframe-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: #999;
}

.preview-placeholder p {
  margin: 0;
  font-size: 16px;
}

/* 版本时间线 */
.version-timeline {
  padding: 8px 0;
}

.version-card {
  padding: 12px;
}

.version-card h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.version-card p {
  margin: 0 0 12px;
  font-size: 13px;
  color: #666;
}

.text-muted {
  color: #999 !important;
  font-style: italic;
}

.version-actions {
  display: flex;
  gap: 8px;
}

/* 鍝嶅簲寮?*/
@media (max-width: 768px) {
  .project-info {
    flex-direction: column;
  }

  .info-right {
    width: 100%;
    align-items: stretch;
  }

  .share-section {
    flex-direction: column;
    align-items: stretch;
  }

  .share-input {
    width: 100%;
  }

  .file-list-toolbar {
    flex-direction: column;
  }

  .file-search-input,
  .file-type-filter {
    width: 100%;
  }

  .action-buttons {
    flex-wrap: wrap;
  }
}
</style>
