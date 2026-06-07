<template>
  <div class="page-container">
    <!-- 返回按钮 -->
    <el-button text @click="goBack" class="back-button">
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
        <!-- 拖拽上传区域 -->
        <el-form-item 
          label="选择文件" 
          :error="fileError"
          required
        >
          <div
            class="upload-dragger"
            :class="{ 
              'is-dragover': isDragOver, 
              'has-file': selectedFile,
              'is-error': fileError 
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
              accept=".pdf,.docx,.xlsx"
              @change="handleFileSelect"
            />
            
            <!-- 未选择文件状态 -->
            <template v-if="!selectedFile">
              <el-icon class="upload-icon" :size="48">
                <UploadFilled />
              </el-icon>
              <div class="upload-text">
                <p class="primary-text">
                  将文件拖到此处，或 <em>点击上传</em>
                </p>
                <p class="secondary-text">
                  支持 PDF、DOCX、XLSX 格式，文件大小不超过 50MB
                </p>
              </div>
            </template>
            
            <!-- 已选择文件状态 -->
            <template v-else>
              <div class="file-preview">
                <el-icon class="file-icon" :size="40">
                  <component :is="getFileIcon(selectedFile.name)" />
                </el-icon>
                <div class="file-info">
                  <p class="file-name" :title="selectedFile.name">
                    {{ selectedFile.name }}
                  </p>
                  <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
                <el-button
                  type="danger"
                  circle
                  size="small"
                  class="remove-file-btn"
                  @click.stop="removeFile"
                >
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </template>
          </div>
        </el-form-item>

        <!-- 变更说明 -->
        <el-form-item label="变更说明">
          <el-input
            v-model="changelog"
            type="textarea"
            placeholder="请输入本次上传的变更说明（可选）..."
            :rows="4"
            maxlength="1000"
            show-word-limit
            :disabled="uploading"
          />
        </el-form-item>

        <!-- 上传进度 -->
        <el-form-item v-if="uploading || uploadStatus === 'success' || uploadStatus === 'exception'">
          <div class="upload-progress">
            <el-progress 
              :percentage="uploadProgress" 
              :status="uploadStatus"
              :stroke-width="12"
              :text-inside="true"
            />
            <p v-if="uploading" class="progress-text">
              {{ uploadProgress < 100 ? '正在上传...' : '正在处理...' }}
            </p>
            <p v-else-if="uploadStatus === 'success'" class="progress-text success">
              上传成功
            </p>
            <p v-else-if="uploadStatus === 'exception'" class="progress-text error">
              上传失败，请重试
            </p>
          </div>
        </el-form-item>

        <!-- 错误提示 -->
        <el-alert
          v-if="uploadError"
          :title="uploadError"
          type="error"
          show-icon
          :closable="false"
          class="upload-error"
        />

        <!-- 操作按钮 -->
        <el-form-item class="action-buttons">
          <el-button 
            @click="goBack" 
            :disabled="uploading"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFile || uploadStatus === 'success'"
            @click="handleUpload"
          >
            <el-icon v-if="!uploading"><Upload /></el-icon>
            {{ uploadButtonText }}
          </el-button>
          <el-button
            v-if="uploadStatus === 'exception'"
            type="primary"
            @click="retryUpload"
          >
            <el-icon><RefreshRight /></el-icon>
            重试
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 上传提示卡片 -->
    <el-card shadow="never" class="tips-card">
      <template #header>
        <span>上传须知</span>
      </template>
      <ul class="tips-list">
        <li>支持 PDF、DOCX、XLSX 格式的文档</li>
        <li>单个文件大小不超过 50MB</li>
        <li>上传新版本时会自动与上一版本进行差异比对</li>
        <li>建议在变更说明中简要描述本次修改内容</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  ArrowLeft, 
  UploadFilled, 
  Upload, 
  Document, 
  Grid, 
  Close,
  RefreshRight
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadFile, uploadVersion } from '@/api/file'
import { useLoading } from '@/composables/useLoading'
import { useMessage } from '@/composables/useMessage'
import { validateFile } from '@/utils/validators'
import { ErrorHandler } from '@/utils/error'
import { formatFileSize } from '@/utils'

// ==================== 路由 ====================
const route = useRoute()
const router = useRouter()

// ==================== 响应式数据 ====================
const fileInputRef = ref(null)
const selectedFile = ref(null)
const changelog = ref('')
const isDragOver = ref(false)
const fileError = ref('')
const uploadError = ref('')

// 上传进度
const uploadProgress = ref(0)
const uploadStatus = ref('') // '' | 'success' | 'exception'

// ==================== 常量 ====================
const ALLOWED_TYPES = ['.pdf', '.docx', '.xlsx']
const MAX_SIZE = 50 * 1024 * 1024 // 50MB

// ==================== 计算属性 ====================
const isVersionUpload = computed(() => !!route.query.fileId)

const uploadButtonText = computed(() => {
  if (uploading.value) {
    return uploadProgress.value < 100 ? '上传中...' : '处理中...'
  }
  return isVersionUpload.value ? '上传新版本' : '开始上传'
})

// ==================== 加载状态 ====================
const { loading: uploading, start: startUploading, stop: stopUploading } = useLoading()
const { success, error: showError } = useMessage()

// ==================== 生命周期 ====================
onUnmounted(() => {
  // 清理可能存在的临时 URL
  if (selectedFile.value?.previewUrl) {
    URL.revokeObjectURL(selectedFile.value.previewUrl)
  }
})

// ==================== 方法 ====================

/**
 * 返回项目详情页
 */
function goBack() {
  router.push(`/admin/projects/${route.params.id}`)
}

/**
 * 触发文件选择
 */
function triggerFileInput() {
  if (!uploading.value) {
    fileInputRef.value?.click()
  }
}

/**
 * 处理拖拽进入
 */
function handleDragEnter() {
  if (!uploading.value) {
    isDragOver.value = true
  }
}

/**
 * 处理拖拽离开
 */
function handleDragLeave() {
  isDragOver.value = false
}

/**
 * 处理拖拽悬停
 * @param {DragEvent} event
 */
function handleDragOver(event) {
  event?.preventDefault?.()
}

/**
 * 处理文件拖放
 * @param {DragEvent} event
 */
function handleDrop(event) {
  isDragOver.value = false
  if (uploading.value) return
  
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    validateAndSetFile(files[0])
  }
}

/**
 * 处理文件选择
 * @param {Event} event
 */
function handleFileSelect(event) {
  const files = event?.target?.files || event?.currentTarget?.files || event?.files || fileInputRef.value?.files
  if (files && files.length > 0) {
    validateAndSetFile(files[0])
  }
}

/**
 * 校验并设置文件
 * @param {File} file
 */
function validateAndSetFile(file) {
  // 清除之前的错误
  fileError.value = ''
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0
  
  // 校验文件
  const result = validateFile(file, {
    maxSize: MAX_SIZE,
    allowedTypes: ALLOWED_TYPES
  })
  
  if (result !== true) {
    fileError.value = result
    showError(result)
    return
  }
  
  selectedFile.value = file
  success('文件已选择')
}

/**
 * 移除已选文件
 */
function removeFile() {
  selectedFile.value = null
  fileError.value = ''
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0
  
  // 重置文件输入
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

/**
 * 处理上传
 */
async function handleUpload() {
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
      uploadProgress.value = progress
    }
    
    if (isVersionUpload.value) {
      // 上传新版本
      await uploadVersion(
        route.query.fileId,
        selectedFile.value,
        changelog.value,
        onProgress
      )
    } else {
      // 上传新文件
      await uploadFile(
        route.params.id,
        selectedFile.value,
        changelog.value,
        onProgress
      )
    }
    
    uploadStatus.value = 'success'
    uploadProgress.value = 100
    success(isVersionUpload.value ? '新版本上传成功' : '文件上传成功')
    
    // 延迟返回
    setTimeout(() => {
      router.push(`/admin/projects/${route.params.id}`)
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

/**
 * 重试上传
 */
function retryUpload() {
  uploadError.value = ''
  uploadStatus.value = ''
  uploadProgress.value = 0
  handleUpload()
}

/**
 * 获取文件图标
 * @param {string} filename
 * @returns {string}
 */
function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  switch (ext) {
    case 'pdf':
      return Document
    case 'docx':
    case 'doc':
      return Document
    case 'xlsx':
    case 'xls':
      return Grid
    default:
      return Document
  }
}
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
  border: 2px dashed var(--border-color-dark, #b8c4d2);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
  background-color: var(--surface-muted, #f6f8fb);
  position: relative;
  overflow: hidden;
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

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-icon {
  color: var(--text-tertiary, #7a8798);
  margin-bottom: 16px;
}

.upload-text .primary-text {
  font-size: 16px;
  color: var(--text-secondary, #475569);
  margin: 0 0 8px;
}

.upload-text .primary-text em {
  color: var(--workspace-blue, #2f5d8c);
  font-style: normal;
  font-weight: 500;
}

.upload-text .secondary-text {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
  margin: 0;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: left;
}

.file-icon {
  color: var(--workspace-blue, #2f5d8c);
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #172033);
  margin: 0 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
  margin: 0;
}

.remove-file-btn {
  flex-shrink: 0;
}

.upload-progress {
  width: 100%;
}

.progress-text {
  text-align: center;
  margin: 8px 0 0;
  font-size: 13px;
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
  margin-top: 24px;
  padding-top: 16px;
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
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #475569);
  font-size: 13px;
  line-height: 2;
}

.tips-list li {
  margin-bottom: 4px;
}
</style>
