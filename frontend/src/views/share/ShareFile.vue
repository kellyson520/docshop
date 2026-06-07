<template>
  <div class="share-file">
    <!-- 返回按钮 -->
    <el-button text @click="goBack" class="back-btn">
      <el-icon><ArrowLeft /></el-icon>
      返回文件列表
    </el-button>

    <!-- 骨架屏 -->
    <template v-if="loading && !error">
      <el-card shadow="never" class="file-info-card">
        <el-skeleton :rows="1" animated />
      </el-card>
      <el-card shadow="never" class="version-card">
        <el-skeleton :rows="4" animated />
      </el-card>
    </template>

    <!-- 文件信息 -->
    <el-card v-if="fileInfo" shadow="never" class="file-info-card">
      <div class="file-info">
        <div class="file-info-main">
          <h3 class="file-name">{{ fileInfo.original_filename }}</h3>
          <div class="file-meta">
            <el-tag size="small" :type="getFileTypeTagType(fileInfo.file_type)" effect="light">
              {{ fileInfo.file_type?.toUpperCase() }}
            </el-tag>
            <span class="meta-item">{{ formatFileSize(fileInfo.file_size) }}</span>
            <span class="meta-item">{{ formatDate(fileInfo.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 版本历史 -->
    <el-card v-if="fileInfo" shadow="never" class="version-card">
      <template #header>
        <span class="card-title">版本历史</span>
      </template>

      <el-timeline v-if="versions.length > 0">
        <el-timeline-item
          v-for="version in versions"
          :key="version.id"
          :timestamp="formatDate(version.created_at)"
          placement="top"
          :type="version.id === versions[0].id ? 'primary' : 'info'"
        >
          <el-card shadow="never" class="version-item-card">
            <div class="version-header">
              <div class="version-info">
                <el-tag :type="version.id === versions[0].id ? 'primary' : 'info'" size="small" effect="light">
                  v{{ version.version }}
                </el-tag>
                <span v-if="version.id === versions[0].id" class="latest-badge">最新</span>
              </div>
              <div class="version-actions">
                <el-dropdown @command="(fmt) => handleDownload(version, fmt)" trigger="click">
                  <el-button type="success" size="small" class="action-btn">
                    <el-icon><Download /></el-icon>
                    下载
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
                <el-button
                  v-if="versionIndex(version) < versions.length - 1"
                  type="warning"
                  size="small"
                  @click="goToDiff(version.id)"
                  class="action-btn"
                >
                  <el-icon><Sort /></el-icon>
                  查看变更
                </el-button>
              </div>
            </div>
            <!-- Diff 摘要 -->
            <div v-if="versionDiff(version)" class="diff-mini">
              <span v-if="versionDiff(version).paragraphs_added" class="diff-stat add">+{{ versionDiff(version).paragraphs_added }} 新增</span>
              <span v-if="versionDiff(version).paragraphs_deleted" class="diff-stat del">-{{ versionDiff(version).paragraphs_deleted }} 删除</span>
              <span v-if="versionDiff(version).paragraphs_modified" class="diff-stat mod">~{{ versionDiff(version).paragraphs_modified }} 修改</span>
            </div>
            <p v-if="version.changelog" class="version-changelog">{{ version.changelog }}</p>
            <p v-else-if="!versionDiff(version)" class="version-changelog no-changelog">无变更说明</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <el-empty v-else description="暂无版本记录" />
    </el-card>

    <!-- 错误状态 -->
    <el-card v-if="error" shadow="never" class="error-card">
      <el-result icon="error" title="访问失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShareFile, getShareVersions, getShareDiffs } from '@/api/share'
import { formatDate, formatFileSize, downloadViaIframe } from '@/utils'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const fileId = route.params.fileId

const fileInfo = ref(null)
const versions = ref([])
const diffMap = ref({})
const loading = ref(false)
const error = ref('')

function versionDiff(version) {
  const d = diffMap.value[version.id]
  if (!d || !d.diff_data) return null
  const parsed = typeof d.diff_data === 'string' ? JSON.parse(d.diff_data) : d.diff_data
  return parsed.stats || null
}

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function versionIndex(version) {
  return versions.value.findIndex((v) => v.id === version.id)
}

function goBack() {
  router.push(`/s/${token}`)
}

function goToDiff(versionId) {
  router.push(`/s/${token}/diff/${fileId}?version_id=${versionId}`)
}

function handleDownload(version, format) {
  // 直接让浏览器处理下载链接，绕过广告拦截器
  const url = `/api/v1/share/${token}/files/${fileId}/versions/${version.id}/download/${format}`
  downloadViaIframe(url)
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [fileData, versionsData, diffsData] = await Promise.all([
      getShareFile(token, fileId),
      getShareVersions(token, fileId),
      getShareDiffs(token, fileId).catch(() => ({ diffs: [] }))
    ])
    fileInfo.value = fileData
    versions.value = versionsData.versions || versionsData || []
    // 建立 diff 映射：new_version_id -> diff
    const map = {}
    for (const d of (diffsData.diffs || [])) {
      // d.new_version 是版本号(int)，用 versions 列表转换为 version id(UUID)
      const v = versions.value.find(v => v.version === d.new_version)
      if (v) map[v.id] = d
    }
    diffMap.value = map
  } catch {
    error.value = '文件不存在或无权访问'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.share-file {
  animation: fadeIn var(--transition-normal);
}

.back-btn {
  margin-bottom: 16px;
  color: var(--text-secondary, #666666);
  transition: all var(--transition-fast);
}

.back-btn:hover {
  color: var(--color-primary, #1A5276);
  transform: translateX(-4px);
}

.file-info-card {
  margin-bottom: 20px;
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}

.file-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #333333);
  margin: 0 0 8px 0;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary, #666666);
  font-size: 13px;
}

.meta-item {
  color: var(--text-tertiary, #999999);
}

.version-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}

.card-title {
  font-weight: 600;
  color: var(--text-primary, #333333);
}

.version-item-card {
  margin-bottom: 0;
  border-radius: var(--radius-md, 8px);
  background-color: var(--bg-tertiary, #fafafa);
  border: 1px solid var(--border-color-light, #ebeef5);
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.version-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.latest-badge {
  color: var(--color-primary, #1A5276);
  font-size: 12px;
  font-weight: 600;
}

.version-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  transition: all var(--transition-fast);
}

.action-btn:hover {
  transform: translateY(-1px);
}

.version-changelog {
  color: var(--text-secondary, #666666);
  font-size: 13px;
  margin: 0;
  line-height: 1.6;
}

.version-changelog.no-changelog {
  color: var(--text-placeholder, #c0c4cc);
  font-style: italic;
}
.diff-mini { display: flex; gap: 10px; margin-bottom: 6px; }
.diff-stat { font-size: 12px; font-weight: 600; padding: 1px 6px; border-radius: 4px; }
.diff-stat.add { background: #dcfce7; color: #166534; }
.diff-stat.del { background: #fee2e2; color: #991b1b; }
.diff-stat.mod { background: #fef3c7; color: #92400e; }

.error-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .file-name {
    font-size: 16px;
  }

  .version-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .version-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
