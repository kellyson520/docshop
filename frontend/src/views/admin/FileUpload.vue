<template>
  <div class="page-container">
    <el-button text class="back-button" @click="goBack">
      <el-icon><ArrowLeft /></el-icon>
      返回项目详情
    </el-button>

    <el-card shadow="never" class="upload-card">
      <template #header>
        <div class="card-header">
          <h3>{{ isVersionUpload ? '上传新版本' : '上传文件' }}</h3>
          <el-tag v-if="isVersionUpload" type="warning">版本更新</el-tag>
        </div>
      </template>

      <el-form label-position="top" class="upload-form">
        <el-form-item label="选择文件" :error="fileError" required>
          <div
            class="upload-dragger"
            :class="{
              'is-dragover': isDragOver,
              'has-file': !!selectedFileName,
              'is-error': !!fileError,
              'is-uploading': uploading,
            }"
            @dragenter.prevent="handleDragEnter"
            @dragleave.prevent="handleDragLeave"
            @dragover="handleDragOver"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <input
              ref="fileInputRef"
              type="file"
              class="file-input"
              :accept="acceptTypes"
              @change="handleFileSelect"
            />

            <template v-if="!selectedFileName">
              <el-icon class="upload-icon" :size="48">
                <UploadFilled />
              </el-icon>
              <div class="upload-text">
                <p class="primary-text">
                  将文件拖到此处，或 <em>点击上传</em>
                </p>
                <p class="secondary-text">
                  支持 PDF、Office、Archive、Video，单个文件不超过 50MB
                </p>
                <p class="secondary-text secondary-text--caps">
                  压缩包支持结构预览，支持结构对比；视频支持媒体播放
                </p>
              </div>
            </template>

            <template v-else>
              <div class="file-preview">
                <el-icon class="file-icon" :size="40">
                  <component :is="getFileIcon(selectedFileName)" />
                </el-icon>
                <div class="file-info">
                  <p class="file-name" :title="selectedFileName">{{ selectedFileName }}</p>
                  <p class="file-size">{{ formatFileSize(selectedFileSize) }}</p>
                </div>
                <el-button
                  type="danger"
                  circle
                  size="small"
                  class="remove-file-btn"
                  :disabled="uploading"
                  @click.stop="removeFile"
                >
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </template>
          </div>
        </el-form-item>

        <el-alert
          v-if="selectedProfile"
          :title="selectedProfile.can_preview ? '支持在线预览' : '当前仅支持下载'"
          type="info"
          show-icon
          :closable="false"
          class="capability-alert"
        />

        <div v-if="selectedProfile" class="capability-badges">
          <span v-if="selectedProfile.preview_mode === 'structure'" class="capability-badge">
            支持结构预览
          </span>
          <span v-if="selectedProfile.can_diff_structural" class="capability-badge">
            支持结构对比
          </span>
          <span v-if="selectedProfile.preview_mode === 'converted'" class="capability-badge">
            支持转换预览
          </span>
          <span v-if="selectedProfile.can_play" class="capability-badge">
            支持媒体播放
          </span>
        </div>

        <el-form-item label="变更说明">
          <el-input
            v-model="changelog"
            type="textarea"
            placeholder="请输入本次上传的变更说明（可选）"
            :rows="4"
            maxlength="1000"
            show-word-limit
            :disabled="uploading"
          />
        </el-form-item>

        <el-form-item v-if="uploading || uploadStatus === 'success' || uploadStatus === 'exception'">
          <div class="upload-progress">
            <el-progress
              :percentage="uploadProgress"
              :status="uploadStatus"
              :stroke-width="12"
              :text-inside="true"
            />
            <p v-if="uploading" class="progress-text">
              {{ uploadProgress < 100 ? '正在上传...' : '正在处理预览...' }}
            </p>
            <p v-else-if="uploadStatus === 'success'" class="progress-text success">上传成功</p>
            <p v-else-if="uploadStatus === 'exception'" class="progress-text error">上传失败，请重试</p>
          </div>
        </el-form-item>

        <el-alert
          v-if="uploadError"
          :title="uploadError"
          type="error"
          show-icon
          :closable="false"
          class="upload-error"
        />

        <el-form-item class="action-buttons">
          <el-button :disabled="uploading" @click="goBack">取消</el-button>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFileName || uploadStatus === 'success'"
            @click="handleUpload"
          >
            <el-icon v-if="!uploading"><Upload /></el-icon>
            {{ uploadButtonText }}
          </el-button>
          <el-button v-if="uploadStatus === 'exception'" type="primary" @click="retryUpload">
            <el-icon><RefreshRight /></el-icon>
            重试
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="tips-card">
      <template #header>
        <span>上传须知</span>
      </template>
      <ul class="tips-list">
        <li>支持 PDF、Office、Archive、Video 等文件格式</li>
        <li>单个文件大小不超过 50MB</li>
        <li>上传新版本后会自动刷新预览与版本信息</li>
        <li>建议填写变更说明，便于后续追踪版本内容</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Close,
  Document,
  Grid,
  RefreshRight,
  Upload,
  UploadFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import client from '@/api/client'
import { uploadFile, uploadVersion } from '@/api/file'
import { useLoading } from '@/composables/useLoading'
import { useMessage } from '@/composables/useMessage'
import { ErrorHandler } from '@/utils/error'
import { deriveClientProfile } from '@/utils/filePreview'
import { formatFileSize } from '@/utils'
import { validateFile } from '@/utils/validators'

const route = useRoute()
const router = useRouter()

const fileInputRef = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const selectedFileSize = ref(0)
const selectedProfile = ref(null)
const changelog = ref('')
const isDragOver = ref(false)
const fileError = ref('')
const uploadError = ref('')
const uploadProgress = ref(0)
const uploadStatus = ref('')
const allowedTypes = ref(['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.7z', '.mp4', '.webm'])

const MAX_SIZE = 50 * 1024 * 1024

const isVersionUpload = computed(() => Boolean(route.query.fileId))
const acceptTypes = computed(() => allowedTypes.value.join(','))
const { loading: uploading, start: startUploading, stop: stopUploading } = useLoading()
const { success, error: showError } = useMessage()

const uploadButtonText = computed(() => {
  if (uploading.value) {
    return uploadProgress.value < 100 ? '上传中...' : '处理中...'
  }
  return isVersionUpload.value ? '上传新版本' : '开始上传'
})

function goBack() {
  router.push(`/admin/projects/${route.params.id || ''}`)
}

function normalizeAllowedTypes(fileTypes) {
  if (!Array.isArray(fileTypes)) return []
  return fileTypes
    .map((item) => String(item || '').trim().toLowerCase())
    .filter(Boolean)
    .map((item) => (item.startsWith('.') ? item : `.${item}`))
}

async function fetchAllowedTypes() {
  try {
    const data = await client.get('/settings')
    const nextTypes = normalizeAllowedTypes(data?.file_types)
    if (nextTypes.length) {
      allowedTypes.value = nextTypes
    }
  } catch {
    // Keep local defaults when backend settings are temporarily unavailable.
  }
}

function resetFileInput() {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function triggerFileInput(event) {
  if (event?.target === fileInputRef.value) return
  if (uploading.value) return
  resetFileInput()
  fileInputRef.value?.click()
}

function handleDragEnter() {
  if (!uploading.value) {
    isDragOver.value = true
  }
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDragOver(event) {
  event?.preventDefault?.()
}

function handleDrop(event) {
  isDragOver.value = false
  if (uploading.value) return
  const files = event?.dataTransfer?.files
  if (files?.length) {
    validateAndSetFile(files[0])
  }
}

function handleFileSelect(event) {
  const files =
    event?.target?.files ||
    event?.currentTarget?.files ||
    event?.files ||
    fileInputRef.value?.files

  if (files?.length) {
    validateAndSetFile(files[0])
  }
}

function validateAndSetFile(file) {
  fileError.value = ''
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0

  const result = validateFile(file, {
    maxSize: MAX_SIZE,
    allowedTypes: allowedTypes.value,
  })

  if (result !== true) {
    fileError.value = result
    showError(result)
    return
  }

  selectedFile.value = file
  selectedFileName.value = file?.name || ''
  selectedFileSize.value = file?.size || 0
  selectedProfile.value = deriveClientProfile(selectedFileName.value)
  success('文件已选择')
}

function removeFile() {
  selectedFile.value = null
  selectedFileName.value = ''
  selectedFileSize.value = 0
  selectedProfile.value = null
  fileError.value = ''
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0
  resetFileInput()
}

async function handleUpload() {
  if (uploading.value) return

  if (!selectedFile.value) {
    fileError.value = '请先选择文件'
    return
  }

  startUploading()
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0

  try {
    const onProgress = (progress) => {
      if (typeof progress === 'number' && !Number.isNaN(progress)) {
        uploadProgress.value = Math.max(0, Math.min(100, Math.round(progress)))
      }
    }

    let uploadResult

    if (isVersionUpload.value) {
      uploadResult = await uploadVersion(
        String(route.query.fileId || ''),
        selectedFile.value,
        changelog.value,
        onProgress,
      )
      ElMessage.success('新版本上传成功')
    } else {
      uploadResult = await uploadFile(
        String(route.params.id || ''),
        selectedFile.value,
        changelog.value,
        onProgress,
        { folder_id: String(route.query.folder_id || '') },
      )
      ElMessage.success('文件上传成功')
    }

    uploadProgress.value = 100
    uploadStatus.value = 'success'

    setTimeout(() => {
      const query = {}
      if (!isVersionUpload.value && route.query.folder_id) {
        query.folder_id = String(route.query.folder_id)
      }
      if (isVersionUpload.value) {
        query.refreshFileId = String(route.query.fileId || '')
        if (uploadResult?.latest_version !== undefined && uploadResult?.latest_version !== null) {
          query.latestVersion = String(uploadResult.latest_version)
        }
        if (uploadResult?.preview_refresh_token) {
          query.previewRefreshToken = String(uploadResult.preview_refresh_token)
        }
      }
      router.push({
        path: `/admin/projects/${route.params.id || ''}`,
        query,
      })
    }, 1500)
  } catch (error) {
    uploadProgress.value = 0
    uploadStatus.value = 'exception'
    uploadError.value = ErrorHandler.parseError(error).message
    ErrorHandler.handle(error, { silent: true })
  } finally {
    stopUploading()
  }
}

function retryUpload() {
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0
  handleUpload()
}

function getFileIcon(filename = '') {
  const ext = filename.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'xlsx':
    case 'xls':
      return Grid
    case 'pdf':
    case 'docx':
    case 'doc':
    default:
      return Document
  }
}

onMounted(() => {
  fetchAllowedTypes()
})
</script>

<style scoped>
.back-button {
  margin-bottom: 16px;
}

.upload-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.upload-form {
  max-width: 600px;
}

.upload-dragger {
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  border: 2px dashed var(--border-color-dark, #b8c4d2);
  border-radius: 8px;
  background-color: var(--surface-muted, #f6f8fb);
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.upload-dragger:hover {
  border-color: var(--workspace-blue, #2f5d8c);
  background-color: #f3f7fb;
  box-shadow: 0 8px 20px rgba(47, 93, 140, 0.08);
}

.upload-dragger.is-dragover {
  border-color: var(--workspace-blue, #2f5d8c);
  background-color: #e6eef5;
}

.upload-dragger.has-file {
  padding: 20px;
  border-style: solid;
  border-color: var(--workspace-accent, #0f766e);
  background-color: #edf8f6;
}

.upload-dragger.is-error {
  border-color: var(--color-danger, #b42318);
  background-color: #fff4f2;
}

.upload-dragger.is-uploading {
  cursor: not-allowed;
}

.file-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-icon {
  margin-bottom: 16px;
  color: var(--text-tertiary, #7a8798);
}

.upload-text .primary-text {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--text-secondary, #475569);
}

.upload-text .primary-text em {
  font-style: normal;
  font-weight: 500;
  color: var(--workspace-blue, #2f5d8c);
}

.upload-text .secondary-text {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
}

.upload-text .secondary-text--caps {
  margin-top: 6px;
}

.file-preview {
  display: flex;
  gap: 16px;
  align-items: center;
  text-align: left;
}

.file-icon {
  flex-shrink: 0;
  color: var(--workspace-blue, #2f5d8c);
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  margin: 0 0 4px;
  overflow: hidden;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #172033);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
}

.remove-file-btn {
  flex-shrink: 0;
}

.capability-alert {
  margin-bottom: 12px;
}

.capability-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 18px;
}

.capability-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.upload-progress {
  width: 100%;
}

.progress-text {
  margin: 8px 0 0;
  font-size: 13px;
  text-align: center;
  color: var(--text-secondary, #475569);
}

.progress-text.success {
  color: var(--workspace-accent, #0f766e);
}

.progress-text.error {
  color: var(--color-danger, #b42318);
}

.upload-error {
  margin-bottom: 16px;
}

.action-buttons {
  padding-top: 16px;
  margin-top: 24px;
  border-top: 1px solid var(--border-color-light, #e4e9f0);
}

.tips-card {
  background-color: var(--surface-muted, #f6f8fb);
}

.tips-card :deep(.el-card__header) {
  padding: 12px 20px;
  font-weight: 500;
  color: var(--text-secondary, #475569);
}

.tips-list {
  padding-left: 20px;
  margin: 0;
  font-size: 13px;
  line-height: 2;
  color: var(--text-secondary, #475569);
}

.tips-list li {
  margin-bottom: 4px;
}
</style>
