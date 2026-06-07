<template>
  <div class="share-project">
    <!-- 楠ㄦ灦灞?-->
    <template v-if="loading && !error">
      <el-card shadow="never" class="project-info-card">
        <el-skeleton :rows="2" animated />
      </el-card>
      <el-card shadow="never" class="file-list-card">
        <el-skeleton :rows="6" animated />
      </el-card>
    </template>

    <!-- 椤圭洰淇℃伅 -->
    <el-card v-if="project" shadow="never" class="project-info-card">
      <h2 class="project-title">{{ project.name }}</h2>
      <p class="project-desc">{{ project.description || '暂无描述' }}</p>
    </el-card>

    <!-- 鏂囦欢鍒楄〃 -->
    <el-card v-if="project" shadow="never" class="file-list-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">文件列表</span>
          <el-tag type="info" effect="plain">共 {{ files.length }} 个文件</el-tag>
        </div>
      </template>

      <el-table :data="files" stripe class="file-table">
        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-name">
              <el-icon :size="18" class="file-icon"><component :is="getFileTypeIcon(row.file_type)" /></el-icon>
              <span class="file-name-text">{{ row.original_filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getFileTypeTagType(row.file_type)" effect="light">
              {{ row.file_type?.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最新版本" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">v{{ row.current_version || 1 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最新变更" min-width="200">
          <template #default="{ row }">
            <span class="changelog text-truncate">{{ row.latest_changelog || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" align="left">
          <template #default="{ row }">
            <el-button text type="info" size="small" @click="previewFile(row)" class="action-btn">
              <el-icon><View /></el-icon> 预览
            </el-button>
            <el-button text type="primary" size="small" @click="goToFile(row.id)" class="action-btn">
              <el-icon><Clock /></el-icon> 版本
            </el-button>
            <el-button text type="warning" size="small" @click="goToDiff(row.id)" class="action-btn">
              <el-icon><Sort /></el-icon> 变更
            </el-button>
            <el-dropdown @command="(fmt) => handleDownloadLatest(row, fmt)" trigger="click">
              <el-button text type="success" size="small" class="action-btn">
                <el-icon><Download /></el-icon> 下载
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="docx">
                    <el-icon><Document /></el-icon> Word 下载
                  </el-dropdown-item>
                  <el-dropdown-item command="pdf">
                    <el-icon><Document /></el-icon> PDF 下载
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="files.length === 0" description="鏆傛棤鏂囦欢" />
    </el-card>

    <!-- 閿欒鐘舵€?-->
    <el-card v-if="error" shadow="never" class="error-card">
      <el-result icon="error" title="璁块棶澶辫触" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="$router.push('/')">杩斿洖棣栭〉</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShareProject } from '@/api/share'
import { formatDate, getFileTypeIcon, downloadViaIframe } from '@/utils'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const project = ref(null)
const files = ref([])
const loading = ref(false)
const error = ref('')

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function goToFile(fileId) {
  router.push(`/s/${token}/files/${fileId}`)
}

function goToDiff(fileId) {
  router.push(`/s/${token}/diff/${fileId}`)
}

function previewFile(file) {
  // 鎵€鏈夋枃浠剁被鍨嬬粺涓€鏂扮獥鍙ｉ瑙堬紙DOCX鈫扨DF 鍐呭祵锛孭DF鈫掔洿鎺ユ樉绀猴級
  window.open(`/api/v1/share/${token}/files/${file.id}/preview`, '_blank')
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let s = bytes
  while (s >= 1024 && i < 3) { s /= 1024; i++ }
  return s.toFixed(1) + ' ' + u[i]
}

function handleDownloadLatest(file, format) {
  const versions = file.versions || []
  if (versions.length === 0) {
    ElMessage.warning('鏆傛棤鍙敤鐗堟湰')
    return
  }
  const latestVersion = versions[0]
  // 鐩存帴璁╂祻瑙堝櫒澶勭悊涓嬭浇閾炬帴锛岀粫杩囧箍鍛婃嫤鎴櫒
  const url = `/api/v1/share/${token}/files/${file.id}/versions/${latestVersion.id}/download/${format}`
  downloadViaIframe(url)
}

async function fetchProject() {
  loading.value = true
  error.value = ''
  try {
    const data = await getShareProject(token)
    project.value = data
    files.value = data.files || []
  } catch (err) {
    error.value = '椤圭洰涓嶅瓨鍦ㄦ垨璁块棶浠ょ墝鏃犳晥'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProject()
})
</script>

<style scoped>
.share-project {
  animation: fadeIn 160ms ease;
}

.project-info-card {
  margin-bottom: 20px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--border-color-light, #e4e9f0);
}

.project-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary, #333333);
  margin: 0 0 8px 0;
}

.project-desc {
  color: var(--text-secondary, #666666);
  font-size: 14px;
  margin: 0;
}

.file-list-card {
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--border-color-light, #e4e9f0);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 600;
  color: var(--text-primary, #333333);
}

.file-table {
  --el-table-header-bg-color: #f3f6fa;
  --el-table-row-hover-bg-color: #f7fafc;
}

.file-table :deep(.el-table__cell:last-child .cell) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: var(--color-primary, #1A5276);
}

.file-name-text {
  color: var(--text-primary, #333333);
}

.time-text {
  color: var(--text-secondary, #666666);
  font-size: 13px;
}

.changelog {
  color: var(--text-tertiary, #999999);
  font-size: 13px;
  display: block;
  max-width: 200px;
}

.action-btn {
  padding: 4px 6px;
  font-weight: 600;
  transition: color 0.16s ease, background-color 0.16s ease;
}

.action-btn:hover {
  transform: none;
}

.error-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 鍝嶅簲寮忛€傞厤 */
@media (max-width: 768px) {
  .project-title {
    font-size: 18px;
  }

  .file-name-text {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
