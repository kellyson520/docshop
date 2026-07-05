<template>
  <div class="page-container">
    <PageHeader
      title="公告管理"
      subtitle="管理滚动公告、弹窗公告与富内容块配置"
      :breadcrumbs="[{ title: '公告管理' }]"
    >
      <template #actions>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新建公告
        </el-button>
      </template>
    </PageHeader>

    <el-card v-loading="loading" shadow="never" class="announcement-table-card">
      <el-table :data="items" stripe>
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column label="摘要" min-width="220">
          <template #default="{ row }">
            <span class="table-summary">{{ announcementPreviewText(row) || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="展示方式" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ modeLabel(row.display_mode) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="推送方式" width="110">
          <template #default="{ row }">
            <el-tag size="small" type="warning">{{ pushLabel(row.push_method) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <span>{{ row.priority ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch
              :model-value="normalizeActive(row.is_active)"
              @change="toggleActive(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        class="pager"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="fetchList"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑公告' : '新建公告'"
      width="760px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="announcement-dialog admin-viewport-dialog"
      destroy-on-close
    >
      <div class="announcement-editor">
        <el-form :model="form.value" label-position="top">
          <div class="editor-grid">
            <el-form-item label="标题" required>
              <el-input v-model="form.value.title" maxlength="100" placeholder="请输入公告标题" />
            </el-form-item>

            <el-form-item label="摘要">
              <el-input
                v-model="form.value.summary"
                maxlength="160"
                placeholder="用于列表与横幅的简短摘要"
              />
            </el-form-item>
          </div>

          <el-form-item label="正文" required>
            <el-input
              v-model="form.value.content"
              type="textarea"
              :rows="4"
              maxlength="1000"
              placeholder="请输入纯文本正文，兼容旧版公告展示"
            />
          </el-form-item>

          <div class="editor-grid editor-grid--meta">
            <el-form-item label="展示方式">
              <el-select v-model="form.value.display_mode">
                <el-option
                  v-for="option in displayModeOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="推送方式">
              <el-select v-model="form.value.push_method" @change="handlePushMethodChange">
                <el-option
                  v-for="option in pushMethodOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="优先级">
              <el-input-number v-model="form.value.priority" :min="0" :max="100" />
            </el-form-item>

            <el-form-item label="启用状态">
              <select v-model="form.value.is_active" class="native-select">
                <option :value="1">启用</option>
                <option :value="0">停用</option>
              </select>
            </el-form-item>
          </div>

          <div v-if="form.value.push_method === 'timed'" class="editor-grid">
            <el-form-item label="开始时间">
              <el-input
                v-model="form.value.start_time"
                placeholder="2026-06-25T20:00:00Z"
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-input
                v-model="form.value.end_time"
                placeholder="2026-06-26T08:00:00Z"
              />
            </el-form-item>
          </div>

          <el-form-item v-if="form.value.push_method === 'single'" label="目标用户 ID">
            <el-input
              v-model="form.value.target_user_id"
              placeholder="请输入目标用户 UUID"
            />
          </el-form-item>

          <section class="block-section">
            <div class="section-header">
              <div>
                <h3>富内容块</h3>
                <p>可组合段落、代码、按钮、图片和视频块，保存时会原样提交 content_blocks。</p>
              </div>
              <div class="section-actions">
                <el-button size="small" @click="previewVisible = true">弹窗预览</el-button>
              </div>
            </div>

            <AnnouncementBlockEditor v-model="form.value.content_blocks" />
          </section>

          <section class="preview-section">
            <div class="section-header">
              <div>
                <h3>预览</h3>
                <p>优先展示 content_blocks；若为空则回退为正文文本。</p>
              </div>
            </div>

            <div class="preview-card">
              <AnnouncementRenderer v-if="previewBlocks.length" :blocks="previewBlocks" />
              <p v-else class="preview-fallback">{{ form.value.content || '暂无预览内容' }}</p>
            </div>
          </section>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <AnnouncementPreviewDialog
      v-model="previewVisible"
      :title="form.value.title"
      :blocks="previewBlocks"
      :fallback-content="form.value.content"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  createAnnouncement,
  deleteAnnouncement,
  listAnnouncements,
  updateAnnouncement,
} from '@/api/announcement'
import AnnouncementBlockEditor from '@/components/announcement/AnnouncementBlockEditor.vue'
import AnnouncementPreviewDialog from '@/components/announcement/AnnouncementPreviewDialog.vue'
import AnnouncementRenderer from '@/components/announcement/AnnouncementRenderer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEventChannel } from '@/composables/useEventChannel'
import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref('')
const previewVisible = ref(false)
const form = reactive({ value: createDefaultForm() })

const displayModeOptions = [
  { label: '滚动显示', value: 'scroll' },
  { label: '弹窗显示', value: 'popup' },
  { label: '侧边提示', value: 'sidebar' },
  { label: '底部横幅', value: 'bottom' },
]

const pushMethodOptions = [
  { label: '全部用户', value: 'all' },
  { label: '时间段推送', value: 'timed' },
  { label: '单用户推送', value: 'single' },
]

const previewBlocks = computed(() => {
  const normalized = normalizeBlocks(form.value.content_blocks)
  if (normalized.length) return normalized

  const fallbackText = normalizeText(form.value.content)
  return fallbackText ? [{ type: 'paragraph', text: fallbackText }] : []
})

function createDefaultForm() {
  return {
    title: '',
    content: '',
    summary: '',
    content_blocks: [],
    display_mode: 'scroll',
    push_method: 'all',
    target_user_id: '',
    start_time: '',
    end_time: '',
    priority: 0,
    is_active: 1,
  }
}

function createBlock(type = 'paragraph') {
  switch (type) {
    case 'code':
      return { type: 'code', language: 'bash', content: '' }
    case 'button':
      return { type: 'button', label: '', url: '' }
    case 'image':
      return { type: 'image', file_id: '', caption: '' }
    case 'video':
      return { type: 'video', file_id: '', caption: '' }
    case 'paragraph':
    default:
      return { type: 'paragraph', text: '' }
  }
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeActive(value) {
  return value === true || value === 1 || value === '1'
}

function normalizeBlockShape(block) {
  const nextBlock = createBlock(block?.type || 'paragraph')
  Object.keys(block).forEach((key) => {
    if (!(key in nextBlock)) {
      delete block[key]
    }
  })
  Object.assign(block, nextBlock, block)
}

function normalizeBlocksInput(value) {
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return Array.isArray(value) ? value : []
}

function normalizeBlocks(blocks) {
  return normalizeBlocksInput(blocks)
    .map((raw) => {
      const type = raw?.type || 'paragraph'
      const block = createBlock(type)

      if (type === 'paragraph') {
        block.text = normalizeText(raw?.text)
      } else if (type === 'code') {
        block.language = normalizeText(raw?.language) || 'text'
        block.content = typeof raw?.content === 'string' ? raw.content : ''
      } else if (type === 'button') {
        block.label = normalizeText(raw?.label)
        block.url = normalizeText(raw?.url)
      } else if (type === 'image' || type === 'video') {
        block.file_id = normalizeText(raw?.file_id)
        block.caption = normalizeText(raw?.caption)
      }

      return block
    })
    .filter((block) => {
      if (block.type === 'paragraph') return Boolean(block.text)
      if (block.type === 'code') return Boolean(block.content)
      if (block.type === 'button') return Boolean(block.label || block.url)
      if (block.type === 'image' || block.type === 'video') return Boolean(block.file_id)
      return false
    })
}

function announcementPreviewText(item = {}) {
  if (normalizeText(item.summary)) return normalizeText(item.summary)

  const firstBlockText = normalizeBlocksInput(item.content_blocks)
    .map((block) => block?.text || block?.content || block?.label || block?.caption || '')
    .find((value) => normalizeText(value))

  if (firstBlockText) return normalizeText(firstBlockText)
  return normalizeText(item.content)
}

function blockTypeLabel(type) {
  return {
    paragraph: '段落',
    code: '代码',
    button: '按钮',
    image: '图片',
    video: '视频',
  }[type] || type
}

function modeLabel(value) {
  return displayModeOptions.find((option) => option.value === value)?.label || value || '-'
}

function pushLabel(value) {
  return pushMethodOptions.find((option) => option.value === value)?.label || value || '-'
}

function applyFormValue(nextValue = {}) {
  form.value = {
    ...createDefaultForm(),
    ...nextValue,
    content_blocks: normalizeBlocksInput(nextValue.content_blocks).map((block) => ({
      ...createBlock(block?.type || 'paragraph'),
      ...block,
    })),
    is_active: normalizeActive(nextValue.is_active) ? 1 : 0,
  }
}

async function fetchList(nextPage = page.value) {
  page.value = Number(nextPage) || 1
  loading.value = true

  try {
    const data = await listAnnouncements({
      page: page.value,
      page_size: pageSize,
    })

    items.value = Array.isArray(data?.items) ? data.items : []
    total.value = Number(data?.total ?? items.value.length)
  } catch (error) {
    items.value = []
    total.value = 0
    ElMessage.error('公告列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = ''
  previewVisible.value = false
  applyFormValue(createDefaultForm())
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row?.id || ''
  previewVisible.value = false
  applyFormValue({
    ...row,
    summary: row?.summary || '',
    content_blocks: row?.content_blocks || [],
  })
  dialogVisible.value = true
}

function handlePushMethodChange() {
  if (form.value.push_method !== 'timed') {
    form.value.start_time = ''
    form.value.end_time = ''
  }

  if (form.value.push_method !== 'single') {
    form.value.target_user_id = ''
  }
}

function buildPayload() {
  return {
    title: normalizeText(form.value.title),
    content: normalizeText(form.value.content),
    summary: normalizeText(form.value.summary),
    content_blocks: normalizeBlocks(form.value.content_blocks),
    display_mode: form.value.display_mode || 'scroll',
    push_method: form.value.push_method || 'all',
    target_user_id: form.value.push_method === 'single' ? normalizeText(form.value.target_user_id) : '',
    start_time: form.value.push_method === 'timed' ? normalizeText(form.value.start_time) : '',
    end_time: form.value.push_method === 'timed' ? normalizeText(form.value.end_time) : '',
    priority: Number(form.value.priority) || 0,
    is_active: normalizeActive(form.value.is_active) ? 1 : 0,
  }
}

async function handleSave() {
  const payload = buildPayload()

  if (!payload.title) {
    ElMessage.warning('请输入公告标题')
    return
  }

  if (!payload.content) {
    ElMessage.warning('请输入公告正文')
    return
  }

  saving.value = true

  try {
    if (editingId.value) {
      await updateAnnouncement(editingId.value, payload)
      ElMessage.success('公告已更新')
    } else {
      await createAnnouncement(payload)
      ElMessage.success('公告已创建')
    }

    dialogVisible.value = false
    previewVisible.value = false
    await fetchList(page.value)
  } catch (error) {
    ElMessage.error(editingId.value ? '公告更新失败' : '公告创建失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  const nextActive = normalizeActive(row?.is_active) ? 0 : 1

  try {
    await updateAnnouncement(row.id, { is_active: nextActive })
    row.is_active = nextActive
    ElMessage.success(nextActive ? '公告已启用' : '公告已停用')
  } catch (error) {
    ElMessage.error('公告状态更新失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该公告吗？', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await deleteAnnouncement(row.id)
    ElMessage.success('公告已删除')
    await fetchList(page.value)
  } catch (error) {
    ElMessage.error('公告删除失败')
  }
}

useEventChannel({
  topics: ['announcements'],
  onEvent: (event) => {
    if (event?.data?.topic === 'announcements' && String(event?.data?.type || '').startsWith('announcement.')) {
      void fetchList(page.value)
    }
  },
})

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.page-container {
  max-width: 1180px;
  margin: 0 auto;
}

.announcement-table-card {
  overflow: hidden;
}

.table-summary {
  color: #475569;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}

.announcement-editor {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding-right: 6px;
}

.editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.editor-grid--meta {
  align-items: start;
}

.block-section,
.preview-section {
  margin-top: 12px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #172033;
}

.section-header p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.section-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.native-select {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid #d0d5dd;
  border-radius: 10px;
  background: #fff;
  color: #172033;
}

.preview-card {
  padding: 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.preview-fallback {
  margin: 0;
  color: #475569;
  white-space: pre-wrap;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .section-header,
  .section-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .announcement-editor {
    max-height: calc(100vh - 180px);
  }
}
</style>
