<template>
  <div class="card-detail" :class="{ 'is-public': isPublicView }">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else-if="card">
      <!-- 公开访问标识 -->
      <div v-if="isPublicView" class="public-banner">
        <div class="banner-content">
          <el-icon :size="20"><Share /></el-icon>
          <span>您正在查看公开分享的文档</span>
          <el-tag type="success" size="small" effect="light" class="public-tag">
            <el-icon><Unlock /></el-icon>
            公开访问
          </el-tag>
        </div>
        <el-button text type="primary" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
      </div>

      <!-- 顶部信息区 -->
      <div class="detail-header">
        <div class="cover-section">
          <img
            v-if="coverSrc && !coverLoadFailed"
            :src="coverSrc"
            alt="cover"
            @error="coverLoadFailed = true"
          />
          <div v-else class="default-cover" :class="card.file_type">
            <el-icon :size="64">
              <component :is="getFileIcon(card.file_type)" />
            </el-icon>
            <span>{{ fileTypeName }}</span>
          </div>
          <!-- 公开/私有标识 -->
          <div class="visibility-badge" :class="card.is_public ? 'public' : 'private'">
            <el-icon>{{ card.is_public ? Unlock : Lock }}</el-icon>
            <span>{{ card.is_public ? '公开' : '私有' }}</span>
          </div>
        </div>
        <div class="info-section">
          <div class="title-row">
            <h1>{{ card.display_name || card.filename }}</h1>
            <el-tag :type="tagType" size="large" effect="light" class="type-tag">
              {{ card.file_type?.toUpperCase() }}
            </el-tag>
          </div>

          <p class="description" v-if="card.description">{{ card.description }}</p>
          <p class="description" v-else><em>暂无描述</em></p>

          <div class="tags" v-if="card.tags?.length">
            <el-tag
              v-for="tag in card.tags"
              :key="tag"
              effect="plain"
              class="tag-item"
              size="small"
            >
              <el-icon><CollectionTag /></el-icon>
              {{ tag }}
            </el-tag>
          </div>

          <div class="meta">
            <div class="meta-item">
              <el-icon><Document /></el-icon>
              <span>文件类型: {{ fileTypeName }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Files /></el-icon>
              <span>版本数: {{ card.versions?.length || card.version_count || 1 }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Clock /></el-icon>
              <span>更新时间: {{ formatDate(card.updated_at) }}</span>
            </div>
            <div class="meta-item" v-if="card.file_size">
              <el-icon><Folder /></el-icon>
              <span>文件大小: {{ formatSize(card.file_size) }}</span>
            </div>
            <div class="meta-item" v-if="card.visit_count !== undefined">
              <el-icon><View /></el-icon>
              <span>浏览次数: {{ formatNumber(card.visit_count) }}</span>
            </div>
            <div class="meta-item" v-if="card.download_count !== undefined">
              <el-icon><Download /></el-icon>
              <span>下载次数: {{ formatNumber(card.download_count) }}</span>
            </div>
          </div>

          <div class="actions">
            <el-button type="primary" size="large" @click="downloadLatest" :loading="downloading">
              <el-icon><Download /></el-icon>
              下载最新版
            </el-button>
            <el-button size="large" @click="showCompare = true" :disabled="!canCompare">
              <el-icon><Sort /></el-icon>
              版本对比
            </el-button>
            <el-button v-if="isAdmin" size="large" @click="goEdit">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button
              v-if="card.is_public"
              size="large"
              type="success"
              plain
              @click="copyShareLink"
            >
              <el-icon><Share /></el-icon>
              分享
            </el-button>
          </div>
        </div>
      </div>

      <!-- 版本历史 -->
      <div class="version-history">
        <div class="section-header">
          <h2>
            <el-icon><Clock /></el-icon>
            版本历史
          </h2>
          <div class="section-actions">
            <el-radio-group v-model="versionViewMode" size="small">
              <el-radio-button label="timeline">
                <el-icon><Timer /></el-icon>
                时间线
              </el-radio-button>
              <el-radio-button label="list">
                <el-icon><List /></el-icon>
                列表
              </el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div v-if="!card.versions?.length" class="empty-versions">
          <el-empty description="暂无版本历史">
            <template #image>
              <div class="custom-empty-icon">
                <el-icon :size="64"><Clock /></el-icon>
              </div>
            </template>
          </el-empty>
        </div>

        <!-- 时间线视图 -->
        <el-timeline v-else-if="versionViewMode === 'timeline'">
          <el-timeline-item
            v-for="(version, index) in card.versions"
            :key="version.id"
            :timestamp="formatDate(version.created_at)"
            placement="top"
            :type="version.is_latest ? 'primary' : 'info'"
            :icon="version.is_latest ? StarFilled : null"
          >
            <el-card shadow="hover" class="version-card" :class="{ 'latest': version.is_latest }">
              <div class="version-item">
                <div class="version-info">
                  <div class="version-header-row">
                    <span class="version-num">
                      v{{ version.version }}
                      <el-tag v-if="version.is_latest" type="success" size="small" effect="light">
                        <el-icon><Check /></el-icon>
                        最新
                      </el-tag>
                      <el-tag v-if="version.is_major" type="warning" size="small" effect="light">
                        <el-icon><Star /></el-icon>
                        重要
                      </el-tag>
                    </span>
                    <span class="version-size" v-if="version.file_size">
                      {{ formatSize(version.file_size) }}
                    </span>
                  </div>
                  <span class="changelog" :class="{ 'no-changelog': !version.changelog }">
                    <el-icon><EditPen /></el-icon>
                    {{ version.changelog || '无变更说明' }}
                  </span>
                </div>
                <div class="version-actions">
                  <el-button size="small" @click="downloadVersion(version.id)" :loading="version.downloading">
                    <el-icon><Download /></el-icon>
                    下载
                  </el-button>
                  <el-button
                    size="small"
                    @click="viewDiff(version)"
                    :disabled="!version.previous_version_id"
                  >
                    <el-icon><Sort /></el-icon>
                    变更
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>

        <!-- 列表视图 -->
        <el-table
          v-else
          :data="card.versions"
          stripe
          class="versions-table"
          :header-cell-style="headerCellStyle"
        >
          <el-table-column label="版本" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_latest ? 'primary' : 'info'" size="small" effect="light">
                v{{ row.version }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_latest" type="success" size="small" effect="light">最新</el-tag>
              <el-tag v-else-if="row.is_major" type="warning" size="small" effect="light">重要</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">历史</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="变更说明" min-width="200">
            <template #default="{ row }">
              <span :class="{ 'text-muted': !row.changelog }">
                <el-icon v-if="row.changelog"><EditPen /></el-icon>
                {{ row.changelog || '无变更说明' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="120" align="center">
            <template #default="{ row }">
              {{ row.file_size ? formatSize(row.file_size) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="downloadVersion(row.id)" :loading="row.downloading">
                <el-icon><Download /></el-icon>
                下载
              </el-button>
              <el-button
                size="small"
                @click="viewDiff(row)"
                :disabled="!row.previous_version_id"
              >
                <el-icon><Sort /></el-icon>
                变更
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 对比按钮 -->
        <div class="compare-action" v-if="selectedVersions.length >= 2">
          <el-button type="primary" @click="showCompare = true">
            对比选中的 {{ selectedVersions.length }} 个版本
          </el-button>
        </div>
      </div>

      <!-- 多版本对比对话框 -->
      <el-dialog
        v-model="showCompare"
        title="多版本对比"
        width="90%"
        :fullscreen="isMobile"
        destroy-on-close
        class="compare-dialog"
      >
        <MultiVersionCompare
          :card-id="card.id"
          :version-ids="selectedVersions"
          :file-type="card.file_type"
        />
      </el-dialog>

      <!-- 单版本变更对话框 -->
      <el-dialog
        v-model="showDiff"
        title="版本变更"
        width="90%"
        :fullscreen="isMobile"
        destroy-on-close
        class="diff-dialog"
      >
        <div v-if="diffLoading" class="diff-loading">
          <el-skeleton :rows="8" animated />
        </div>
        <template v-else-if="diffData">
          <MediaDiffView
            v-if="diffData?.diff_type === 'media'"
            :payload="diffData.payload || {}"
            :summary="diffData.summary || {}"
          />
          <ArchiveDiffView
            v-else-if="diffData?.diff_type === 'structure'"
            :payload="diffData.payload || {}"
            :summary="diffData.summary || {}"
          />
          <DocxDiffView v-else-if="diffData?.diff_type === 'docx_diff' || card.file_type === 'docx'" :diff-data="diffData" />
          <XlsxDiffView v-else-if="card.file_type === 'xlsx'" :diff-data="diffData" />
          <PdfDiffView v-else-if="card.file_type === 'pdf'" :diff-data="diffData" />
          <el-empty v-else description="鏆備笉鏀寔璇ユ枃浠剁被鍨嬬殑瀵规瘮棰勮">
            <template #image>
              <el-icon :size="64"><Document /></el-icon>
            </template>
          </el-empty>
        </template>
      </el-dialog>
    </template>

    <!-- 错误状态 -->
    <div v-else class="error-state">
      <el-result icon="error" title="加载失败" :sub-title="errorMessage">
        <template #extra>
          <el-button type="primary" @click="loadCard">重试</el-button>
          <el-button @click="$router.back()">返回</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { cardApi } from '@/api/card'
import { getDiffs } from '@/api/diff'
import { resolveCoverUrl } from '@/utils/cover'
import MultiVersionCompare from '@/components/compare/MultiVersionCompare.vue'
import ArchiveDiffView from '@/components/diff/ArchiveDiffView.vue'
import DocxDiffView from '@/components/diff/DocxDiffView.vue'
import MediaDiffView from '@/components/diff/MediaDiffView.vue'
import XlsxDiffView from '@/components/diff/XlsxDiffView.vue'
import PdfDiffView from '@/components/diff/PdfDiffView.vue'
import {
  Document,
  Files,
  Clock,
  Folder,
  Download,
  Sort,
  Edit,
  Share,
  Unlock,
  Lock,
  View,
  StarFilled,
  Check,
  Star,
  EditPen,
  HomeFilled,
  Timer,
  List,
  CollectionTag
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const { isMobile } = useResponsive()

// 数据
const card = ref(null)
const coverLoadFailed = ref(false)
const selectedVersions = ref([])
const downloading = ref(false)
const showCompare = ref(false)
const showDiff = ref(false)
const diffData = ref(null)
const diffLoading = ref(false)
const errorMessage = ref('')
const loading = ref(false)
const versionViewMode = ref('timeline')

// 计算属性
const fileTypeName = computed(() => {
  const types = {
    pdf: 'PDF 文档',
    docx: 'Word 文档',
    xlsx: 'Excel 表格',
    pptx: 'PPT 演示文稿',
    txt: '文本文件'
  }
  return types[card.value?.file_type] || '文档'
})

const tagType = computed(() => {
  const types = {
    pdf: 'danger',
    docx: 'primary',
    xlsx: 'success',
    pptx: 'warning',
    txt: 'info'
  }
  return types[card.value?.file_type] || 'info'
})

const canCompare = computed(() => {
  return card.value?.versions?.length >= 2
})

const isAdmin = computed(() => {
  // 检查是否为管理员
  return route.path.startsWith('/admin')
})

const isPublicView = computed(() => {
  // 检查是否为公开访问视图
  return route.query.public === '1' || route.meta?.isPublic
})

const coverSrc = computed(() => resolveCoverUrl(card.value?.cover_image))

watch(coverSrc, () => {
  coverLoadFailed.value = false
})

const headerCellStyle = {
  background: '#f5f7fa',
  color: '#606266',
  fontWeight: 600
}

// 获取文件图标
function getFileIcon(fileType) {
  const iconMap = {
    pdf: Document,
    docx: Document,
    xlsx: Files,
    pptx: Document,
    txt: Document
  }
  return iconMap[fileType] || Document
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化文件大小
function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let unitIndex = 0
  let size = bytes
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

// 格式化数字
function formatNumber(num) {
  if (num === undefined || num === null) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

// 方法
async function loadCard() {
  const cardId = route.params.id
  if (!cardId) return

  loading.value = true
  try {
    const data = await cardApi.getDetail(cardId)
    card.value = data

    // 记录访问
    cardApi.recordVisit(cardId).catch(() => {})
  } catch (error) {
    errorMessage.value = error.message || '加载卡片详情失败'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

async function downloadLatest() {
  if (downloading.value) return
  downloading.value = true

  try {
    const blob = await cardApi.downloadLatest(card.value.id)
    triggerDownload(blob, card.value.filename || card.value.display_name)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败: ' + error.message)
  } finally {
    downloading.value = false
  }
}

async function downloadVersion(versionId) {
  try {
    const blob = await cardApi.downloadVersion(card.value.id, versionId)
    const version = card.value.versions?.find(v => v.id === versionId)
    if (!version) {
      ElMessage.error('版本信息未找到')
      return
    }
    const filename = version.filename || `v${version.version}_${card.value.filename}`
    triggerDownload(blob, filename)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败: ' + error.message)
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  try {
    a.click()
  } finally {
    if (a.parentNode) {
      document.body.removeChild(a)
    }
    URL.revokeObjectURL(url)
  }
}

function normalizeDiffPayload(firstDiff) {
  const parsed = typeof firstDiff?.diff_data === 'string'
    ? JSON.parse(firstDiff.diff_data)
    : (firstDiff?.diff_data || {})

  const nextDiffType = firstDiff?.diff_type || parsed?.diff_type
  if (!nextDiffType) {
    return parsed
  }

  return {
    ...parsed,
    diff_type: nextDiffType,
  }
}

async function viewDiff(version) {
  if (!version.previous_version_id) {
    ElMessage.warning('没有可对比的上一版本')
    return
  }

  showDiff.value = true
  diffLoading.value = true

  try {
    const diffResponse = await getDiffs(card.value.id, {
      old_version: version.previous_version_id,
      new_version: version.id
    })
    const firstDiff = diffResponse?.diffs?.[0]
    if (!firstDiff) {
      throw new Error('未找到对应版本差异')
    }
    diffData.value = normalizeDiffPayload(firstDiff)
  } catch (error) {
    ElMessage.error('获取变更失败: ' + error.message)
    showDiff.value = false
  } finally {
    diffLoading.value = false
  }
}

function goEdit() {
  router.push(`/admin/cards/${card.value.id}/edit`)
}

function goHome() {
  router.push('/')
}

function copyShareLink() {
  const shareUrl = `${window.location.origin}/cards/${card.value.id}?public=1`
  navigator.clipboard.writeText(shareUrl).then(() => {
    ElMessage.success('分享链接已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 监听路由变化
watch(() => route.params.id, (newId) => {
  if (newId) {
    selectedVersions.value = []
    loadCard()
  }
})

// 初始化
onMounted(() => {
  loadCard()
})
</script>

<style scoped>
.card-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

/* 公开访问横幅 */
.public-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
  border-radius: 12px;
  margin-bottom: 24px;
  border: 1px solid #d9ecff;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #67c23a;
  font-weight: 500;
}

.banner-content .el-icon {
  font-size: 20px;
}

.public-tag {
  margin-left: 8px;
  font-weight: 500;
}

.public-tag .el-icon {
  margin-right: 4px;
}

.loading-container {
  padding: 40px;
}

/* 顶部信息区 */
.detail-header {
  display: flex;
  gap: 32px;
  margin-bottom: 40px;
  padding: 24px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.cover-section {
  flex-shrink: 0;
  width: 240px;
  height: 320px;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.cover-section img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.default-cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #909399;
}

.default-cover.pdf { color: #f56c6c; }
.default-cover.docx { color: #409eff; }
.default-cover.xlsx { color: #67c23a; }
.default-cover.pptx { color: #e6a23c; }

.visibility-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  backdrop-filter: blur(10px);
}

.visibility-badge.public {
  background: rgba(103, 194, 58, 0.9);
  color: #fff;
}

.visibility-badge.private {
  background: rgba(144, 147, 153, 0.9);
  color: #fff;
}

.info-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-row h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.type-tag {
  font-weight: 500;
}

.description {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.description em {
  color: #c0c4cc;
  font-style: italic;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-item {
  margin: 0;
}

.tag-item .el-icon {
  margin-right: 4px;
}

.meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #909399;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}

/* 版本历史 */
.version-history {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.section-header h2 .el-icon {
  color: #409eff;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.empty-versions {
  padding: 40px;
  text-align: center;
}

.custom-empty-icon {
  color: #dcdfe6;
  margin-bottom: 16px;
}

.version-card {
  margin-bottom: 0;
  border-radius: 8px;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
}

.version-card.latest {
  border: 1px solid #409eff;
  background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%);
}

.version-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.version-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.version-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.version-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.version-num {
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-size {
  font-size: 13px;
  color: #909399;
}

.changelog {
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 6px;
}

.changelog .el-icon {
  color: #409eff;
  font-size: 14px;
}

.changelog.no-changelog {
  color: #c0c4cc;
  font-style: italic;
}

.changelog.no-changelog .el-icon {
  color: #c0c4cc;
}

.version-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 版本表格 */
.versions-table {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.versions-table :deep(.el-table__header th) {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.text-muted {
  color: #c0c4cc;
  font-style: italic;
}

.compare-action {
  margin-top: 24px;
  text-align: center;
}

.diff-loading {
  padding: 20px;
}

.error-state {
  padding: 60px 20px;
}

/* 响应式 */
@media (max-width: 992px) {
  .detail-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .cover-section {
    width: 200px;
    height: 260px;
  }

  .title-row {
    flex-direction: column;
    gap: 12px;
  }

  .meta {
    grid-template-columns: 1fr;
    text-align: left;
  }

  .actions {
    justify-content: center;
  }

  .version-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .version-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .card-detail {
    padding: 16px;
  }

  .public-banner {
    flex-direction: column;
    gap: 12px;
    text-align: center;
  }

  .detail-header {
    padding: 16px;
  }

  .cover-section {
    width: 100%;
    height: 200px;
  }

  .title-row h1 {
    font-size: 20px;
  }

  .version-history {
    padding: 16px;
  }

  .section-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .version-actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .banner-content {
    flex-direction: column;
    gap: 8px;
  }

  .actions .el-button {
    flex: 1;
    min-width: 120px;
  }
}
</style>
