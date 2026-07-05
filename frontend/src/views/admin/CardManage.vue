<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <PageHeader
      title="文档管理"
      :breadcrumbs="breadcrumbs"
      subtitle="管理和编辑所有文档卡片"
    >
      <template #actions>
        <el-button type="primary" @click="showUpload = true" class="btn-hover-lift">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
      </template>
    </PageHeader>

    <!-- 筛选栏 -->
    <div class="filter-bar card-hover">
      <el-input
        v-model="keyword"
        placeholder="搜索文件名、描述..."
        clearable
        @keyup.enter="handleSearch"
        @clear="handleSearch"
        class="search-input input-focus-glow"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="fileType"
        placeholder="文件类型"
        clearable
        @change="handleSearch"
        class="filter-select"
      >
        <template #prefix>
          <el-icon><Document /></el-icon>
        </template>
        <el-option label="PDF" value="pdf" />
        <el-option label="Word" value="docx" />
        <el-option label="Excel" value="xlsx" />
      </el-select>

      <el-select
        v-model="category"
        placeholder="分类"
        clearable
        @change="handleSearch"
        class="filter-select"
      >
        <template #prefix>
          <el-icon><Folder /></el-icon>
        </template>
        <el-option
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        />
      </el-select>

      <el-button
        v-if="selectedCards.length > 0"
        type="danger"
        plain
        @click="handleBatchDelete"
      >
        <el-icon><Delete /></el-icon>
        批量删除 ({{ selectedCards.length }})
      </el-button>
    </div>

    <!-- 标签筛选 -->
    <div class="tag-filter" v-if="allTags.length">
      <span class="tag-label">
        <el-icon><PriceTag /></el-icon>
        标签筛选:
      </span>
      <div class="tag-list">
        <el-tag
          v-for="tag in allTags"
          :key="tag"
          :type="selectedTags.includes(tag) ? 'primary' : 'info'"
          :effect="selectedTags.includes(tag) ? 'dark' : 'light'"
          @click="toggleTag(tag)"
          class="tag-item"
        >
          {{ tag }}
        </el-tag>
        <el-button
          v-if="selectedTags.length"
          text
          type="primary"
          size="small"
          @click="selectedTags = []"
        >
          清除
        </el-button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <CardGrid
      :cards="cards"
      :loading="loading"
      :selected="selectedCards"
      selectable
      @card-click="editCard"
      @selection-change="handleSelectionChange"
    />

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[12, 24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadCards"
        @current-change="loadCards"
      />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="showEdit"
      title="编辑卡片"
      width="600px"
      :fullscreen="isMobile"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="80px" v-if="editForm">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" placeholder="输入显示名称" />
        </el-form-item>
        <el-form-item label="介绍">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="输入文档介绍"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category" placeholder="选择分类" clearable>
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="封面图片">
          <el-upload
            :show-file-list="false"
            @change="handleCoverChange"
            accept="image/*"
            class="cover-uploader"
          >
            <img
              v-if="editForm.cover_image"
              :src="editForm.cover_image"
              class="cover-preview"
            />
            <div v-else class="cover-placeholder">
              <el-icon><Plus /></el-icon>
              <span>上传封面</span>
            </div>
          </el-upload>
          <el-button
            v-if="editForm.cover_image"
            text
            type="danger"
            @click="editForm.cover_image = ''"
          >
            移除封面
          </el-button>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或创建标签"
          >
            <el-option
              v-for="tag in allTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="saveCard" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUpload"
      title="上传文件"
      width="500px"
      :fullscreen="isMobile"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileSelect"
        :on-remove="handleFileRemove"
        :file-list="fileList"
        accept=".pdf,.docx,.xlsx"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF、Word、Excel 文件，单个文件不超过 50MB
          </div>
        </template>
      </el-upload>

      <!-- 上传后自动填充文件名 -->
      <el-form
        :model="uploadForm"
        label-width="80px"
        v-if="selectedFile"
        style="margin-top: 20px;"
      >
        <el-form-item label="文件名">
          <el-input v-model="uploadForm.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="介绍">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="2"
            placeholder="文档介绍（可选）"
          />
        </el-form-item>
        <el-form-item label="变更说明">
          <el-input
            v-model="uploadForm.changelog"
            placeholder="本次上传的变更说明（可选）"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="uploadForm.tags"
            multiple
            filterable
            allow-create
            placeholder="选择或创建标签"
          >
            <el-option
              v-for="tag in allTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeUploadDialog">取消</el-button>
        <el-button
          type="primary"
          @click="uploadFile"
          :loading="uploading"
          :disabled="!selectedFile"
        >
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <el-dialog
      v-model="showDelete"
      title="确认删除"
      width="400px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
    >
      <p>确定要删除卡片 "{{ deleteTarget?.display_name || deleteTarget?.filename }}" 吗？</p>
      <p class="delete-warning">此操作将删除所有版本，且不可恢复！</p>
      <template #footer>
        <el-button @click="showDelete = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete" :loading="deleting">删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'CardManage' })

import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Upload, Plus, UploadFilled, Document, Folder, PriceTag, Delete
} from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'
import { useResponsive } from '@/composables/useResponsive'
import { resolveCoverUrl } from '@/utils/cover'
import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'
import CardGrid from '@/components/card/CardGrid.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const { isMobile } = useResponsive()

// ==================== 面包屑 ====================
const breadcrumbs = [
  { title: '文档管理' }
]

// ==================== 筛选状态 ====================
const keyword = ref('')
const fileType = ref('')
const category = ref('')
const selectedTags = ref([])
const selectedCards = ref([])

// ==================== 数据 ====================
const cards = ref([])
const categories = ref([])
const allTags = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)

// ==================== 编辑对话框 ====================
const showEdit = ref(false)
const editForm = ref(null)
const saving = ref(false)

// ==================== 上传对话框 ====================
const showUpload = ref(false)
const selectedFile = ref(null)
const fileList = ref([])
const uploadForm = reactive({
  display_name: '',
  description: '',
  changelog: '',
  tags: []
})
const uploading = ref(false)
const uploadRef = ref(null)

// ==================== 删除对话框 ====================
const showDelete = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// ==================== 加载卡片列表 ====================
async function loadCards() {
  loading.value = true

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }

    if (keyword.value) params.keyword = keyword.value
    if (fileType.value) params.file_type = fileType.value
    if (category.value) params.category = category.value
    if (selectedTags.value.length) params.tags = selectedTags.value

    const data = await cardApi.getList(params)
    cards.value = data.items || data || []
    total.value = data.total || cards.value.length
  } catch (error) {
    ElMessage.error('加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// ==================== 加载分类 ====================
async function loadCategories() {
  try {
    const data = await cardApi.getCategories()
    categories.value = data || []
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// ==================== 加载标签 ====================
async function loadTags() {
  try {
    const data = await cardApi.getTags()
    allTags.value = data || []
  } catch (error) {
    console.error('加载标签失败:', error)
  }
}

// ==================== 搜索 ====================
function handleSearch() {
  currentPage.value = 1
  loadCards()
}

// ==================== 切换标签筛选 ====================
function toggleTag(tag) {
  const index = selectedTags.value.indexOf(tag)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tag)
  }
  handleSearch()
}

// ==================== 选择变化 ====================
function handleSelectionChange(selection) {
  selectedCards.value = selection.map(card => card.id)
}

// ==================== 批量删除 ====================
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedCards.value.length} 个卡片吗？此操作不可撤销。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )

    for (const id of selectedCards.value) {
      await cardApi.delete(id)
    }
    ElMessage.success(`已删除 ${selectedCards.value.length} 个卡片`)
    selectedCards.value = []
    loadCards()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败: ' + error.message)
    }
  }
}

// ==================== 编辑卡片 ====================
function editCard(card) {
  editForm.value = {
    id: card.id,
    display_name: card.display_name || card.filename,
    description: card.description || '',
    category: card.category || '',
    cover_image: resolveCoverUrl(card.cover_image) || '',
    tags: card.tags || []
  }
  showEdit.value = true
}

// ==================== 保存卡片 ====================
async function saveCard() {
  if (!editForm.value) return

  saving.value = true

  try {
    await cardApi.updateInfo(editForm.value.id, {
      display_name: editForm.value.display_name,
      description: editForm.value.description,
      category: editForm.value.category,
      tags: editForm.value.tags
    })

    // 如果有新封面，上传封面
    if (editForm.value.cover_image && editForm.value.cover_image.startsWith('data:')) {
      // 转换 base64 为 File
      const response = await fetch(editForm.value.cover_image)
      const blob = await response.blob()
      const file = new File([blob], 'cover.jpg', { type: blob.type })
      await cardApi.uploadCover(editForm.value.id, file)
    }

    ElMessage.success('保存成功')
    showEdit.value = false
    loadCards()
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// ==================== 处理封面选择 ====================
function handleCoverChange(file) {
  if (!file.raw) return

  // 检查文件类型
  if (!file.raw.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }

  // 预览图片
  const reader = new FileReader()
  reader.onload = (e) => {
    editForm.value.cover_image = e.target.result
  }
  reader.readAsDataURL(file.raw)
}

// ==================== 处理文件选择 ====================
function handleFileSelect(file) {
  selectedFile.value = file.raw

  // 自动填充文件名（去除扩展名）
  const filename = file.name
  const ext = filename.substring(filename.lastIndexOf('.'))
  const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'))

  uploadForm.display_name = nameWithoutExt
  uploadForm.description = ''
  uploadForm.changelog = ''
  uploadForm.tags = []
}

// ==================== 处理文件移除 ====================
function handleFileRemove() {
  selectedFile.value = null
  fileList.value = []
}

// ==================== 关闭上传对话框 ====================
function closeUploadDialog() {
  showUpload.value = false
  selectedFile.value = null
  fileList.value = []
}

// ==================== 上传文件 ====================
async function uploadFile() {
  if (!selectedFile.value) return

  uploading.value = true

  try {
    // 先创建卡片
    const cardData = await cardApi.create({
      display_name: uploadForm.display_name,
      description: uploadForm.description,
      tags: uploadForm.tags
    })

    // 再上传文件
    await cardApi.uploadFile(cardData.id, selectedFile.value, {
      changelog: uploadForm.changelog
    })

    ElMessage.success('上传成功')
    closeUploadDialog()
    loadCards()
  } catch (error) {
    ElMessage.error('上传失败: ' + error.message)
  } finally {
    uploading.value = false
  }
}

// ==================== 确认删除 ====================
async function confirmDelete() {
  if (!deleteTarget.value) return

  deleting.value = true

  try {
    await cardApi.delete(deleteTarget.value.id)
    ElMessage.success('删除成功')
    showDelete.value = false
    deleteTarget.value = null
    loadCards()
  } catch (error) {
    ElMessage.error('删除失败: ' + error.message)
  } finally {
    deleting.value = false
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  loadCards()
  loadCategories()
  loadTags()
})
</script>

<style scoped>
/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
  padding: 16px;
  background: var(--surface-panel, #fff);
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

[data-theme="dark"] .filter-bar {
  background: var(--bg-secondary, #1d1d1d);
}

.search-input {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.filter-select {
  width: 150px;
}

/* 标签筛选 */
.tag-filter {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--surface-panel, #fff);
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

[data-theme="dark"] .tag-filter {
  background: var(--bg-secondary, #1d1d1d);
}

.tag-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-secondary, #475569);
  white-space: nowrap;
  padding-top: 6px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.tag-item {
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
  border-radius: 8px !important;
}

.tag-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

/* 封面上传 */
.cover-uploader {
  display: inline-block;
}

.cover-preview {
  width: 200px;
  height: 150px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.cover-preview:hover {
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.12);
}

.cover-placeholder {
  width: 200px;
  height: 150px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 2px dashed var(--border-color-dark, #b8c4d2);
  border-radius: 8px;
  color: var(--text-tertiary, #7a8798);
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
  cursor: pointer;
}

.cover-placeholder:hover {
  border-color: var(--workspace-blue, #2f5d8c);
  color: var(--workspace-blue, #2f5d8c);
  background: rgba(47, 93, 140, 0.06);
}

.delete-warning {
  color: var(--color-danger, #b42318);
  font-size: 13px;
  margin-top: 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input,
  .filter-select {
    width: 100%;
    max-width: none;
  }

  .tag-filter {
    flex-direction: column;
    align-items: flex-start;
  }

  .tag-list {
    width: 100%;
  }
}
</style>
