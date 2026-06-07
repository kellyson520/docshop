<template>
  <div class="page-container">
    <PageHeader title="公告管理" subtitle="管理系统公告，支持多种展示模式和推送方式" :breadcrumbs="[{ title: '公告管理' }]">
      <template #actions>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建公告</el-button>
      </template>
    </PageHeader>

    <el-card v-loading="loading" shadow="never">
      <el-table :data="items" stripe>
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column label="展示模式" width="100">
          <template #default="{ row }"><el-tag size="small">{{ modeLabel(row.display_mode) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="推送方式" width="100">
          <template #default="{ row }"><el-tag size="small" type="warning">{{ pushLabel(row.push_method) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active === 1" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" class="pager" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev,pager,next" background @current-change="fetch" />
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑公告' : '新建公告'" width="560px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required><el-input v-model="form.title" maxlength="100" /></el-form-item>
        <el-form-item label="内容" required><el-input v-model="form.content" type="textarea" :rows="3" maxlength="500" /></el-form-item>
        <el-form-item label="展示模式">
          <el-select v-model="form.display_mode">
            <el-option label="滚动显示" value="scroll" />
            <el-option label="弹窗显示" value="popup" />
            <el-option label="侧边显示" value="sidebar" />
            <el-option label="底部显示" value="bottom" />
          </el-select>
        </el-form-item>
        <el-form-item label="推送方式">
          <el-select v-model="form.push_method" @change="onPushChange">
            <el-option label="全部用户" value="all" />
            <el-option label="时间段推送" value="timed" />
            <el-option label="单用户推送" value="single" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.push_method === 'timed'" label="开始时间"><el-input v-model="form.start_time" placeholder="2024-01-01T00:00:00Z" /></el-form-item>
        <el-form-item v-if="form.push_method === 'timed'" label="结束时间"><el-input v-model="form.end_time" placeholder="2024-12-31T23:59:59Z" /></el-form-item>
        <el-form-item v-if="form.push_method === 'single'" label="目标用户ID"><el-input v-model="form.target_user_id" placeholder="用户UUID" /></el-form-item>
        <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" :max="99" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ editingId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import PageHeader from '@/components/common/PageHeader.vue'

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref('')
const form = ref({ title: '', content: '', display_mode: 'scroll', push_method: 'all', target_user_id: '', start_time: '', end_time: '', priority: 0 })

const modeLabel = m => ({ scroll: '滚动', popup: '弹窗', sidebar: '侧边', bottom: '底部' }[m] || m)
const pushLabel = p => ({ all: '全部', timed: '时段', single: '单用户' }[p] || p)

async function fetch() {
  loading.value = true
  try {
    const d = await get('/announcements', { page: page.value, page_size: pageSize })
    items.value = d.items || []
    total.value = d.total || 0
  } finally { loading.value = false }
}

function openCreate() {
  editingId.value = ''
  form.value = { title: '', content: '', display_mode: 'scroll', push_method: 'all', target_user_id: '', start_time: '', end_time: '', priority: 0 }
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

function onPushChange() {
  if (form.value.push_method !== 'timed') { form.value.start_time = ''; form.value.end_time = '' }
  if (form.value.push_method !== 'single') form.value.target_user_id = ''
}

async function handleSave() {
  if (!form.value.title || !form.value.content) { ElMessage.warning('标题和内容不能为空'); return }
  saving.value = true
  try {
    if (editingId.value) {
      await put(`/announcements/${editingId.value}`, form.value)
      ElMessage.success('已更新')
    } else {
      await post('/announcements', form.value)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetch()
  } finally { saving.value = false }
}

async function toggleActive(row) {
  try {
    await put(`/announcements/${row.id}`, { is_active: row.is_active === 1 ? 0 : 1 })
    row.is_active = row.is_active === 1 ? 0 : 1
  } catch { ElMessage.error('操作失败') }
}

async function handleDelete(row) {
  try { await ElMessageBox.confirm('确定删除该公告？', '提示', { type: 'warning' }) } catch { return }
  await del(`/announcements/${row.id}`)
  ElMessage.success('已删除')
  fetch()
}

onMounted(fetch)
</script>

<style scoped>
.page-container { max-width: 1100px; margin: 0 auto; }
.pager { margin-top: 16px; display: flex; justify-content: center; }
</style>
