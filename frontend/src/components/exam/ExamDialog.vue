<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑考试' : '新建考试'"
    width="760px"
    top="5vh"
    append-to-body
    modal-class="exam-dialog-mask"
    destroy-on-close
    :close-on-click-modal="false"
    class="exam-dialog"
    @closed="handleClosed"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="96px"
      label-position="right"
      status-icon
    >
      <div class="field-grid">
        <el-form-item label="考试名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="输入考试名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="关联项目" prop="project_id">
          <el-select
            v-model="form.project_id"
            placeholder="选择关联项目"
            filterable
            :loading="projectStore.loading"
            style="width: 100%"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
      </div>

      <div class="time-grid">
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker
            v-model="form.start_time"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="disabledStartDate"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker
            v-model="form.end_time"
            type="datetime"
            placeholder="选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="disabledEndDate"
            style="width: 100%"
          />
        </el-form-item>
      </div>

      <el-form-item label="考试描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          placeholder="补充考试说明，用户查看考试安排时会看到"
          :rows="2"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="提醒设置">
        <div class="reminder-panel">
          <label class="reminder-option">
            <span>15 分钟前</span>
            <el-switch v-model="form.reminder_15min" :active-value="1" :inactive-value="0" />
          </label>
          <label class="reminder-option">
            <span>5 分钟前</span>
            <el-switch v-model="form.reminder_5min" :active-value="1" :inactive-value="0" />
          </label>
          <label class="reminder-option">
            <span>开始时</span>
            <el-switch v-model="form.reminder_start" :active-value="1" :inactive-value="0" />
          </label>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存修改' : '创建考试' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineOptions({ name: 'ExamDialog' })

import { ref, computed, watch, onMounted } from 'vue'
import { useExamStore } from '@/stores/exam'
import { useProjectStore } from '@/stores/project'
import { useMessage } from '@/composables/useMessage'
import { ErrorHandler } from '@/utils/error'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  exam: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const examStore = useExamStore()
const projectStore = useProjectStore()
const { success } = useMessage()

const formRef = ref(null)
const projects = ref([])
const submitting = ref(false)

const defaultForm = () => ({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  project_id: '',
  reminder_15min: 1,
  reminder_5min: 1,
  reminder_start: 1
})

const form = ref(defaultForm())

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.exam)

const rules = {
  name: [
    { required: true, message: '请输入考试名称', trigger: 'blur' },
    { min: 2, max: 100, message: '名称长度应在 2-100 个字符之间', trigger: 'blur' }
  ],
  project_id: [
    { required: true, message: '请选择关联项目', trigger: 'change' }
  ],
  start_time: [
    { required: true, message: '请选择开始时间', trigger: 'change' }
  ],
  end_time: [
    { required: true, message: '请选择结束时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请选择结束时间'))
          return
        }
        if (!form.value.start_time) {
          callback()
          return
        }
        const startTime = new Date(form.value.start_time)
        const endTime = new Date(value)
        if (endTime <= startTime) {
          callback(new Error('结束时间必须晚于开始时间'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

onMounted(loadProjects)

watch(() => visible.value, (isVisible) => {
  if (isVisible) {
    loadProjects()
    fillForm(props.exam)
  }
})

watch(() => props.exam, (exam) => {
  if (visible.value) {
    fillForm(exam)
  }
}, { immediate: true })

async function loadProjects() {
  if (projectStore.projects.length > 0) {
    projects.value = projectStore.projects
    return
  }

  try {
    const data = await projectStore.fetchProjects({ page_size: 100 })
    projects.value = data.items || data || []
  } catch (err) {
    if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return
    console.warn('[ExamDialog] 加载项目列表失败:', err)
  }
}

function fillForm(exam) {
  if (!exam) {
    resetForm()
    return
  }

  form.value = {
    name: exam.name || '',
    description: exam.description || '',
    start_time: formatDateTimeLocal(exam.start_time),
    end_time: formatDateTimeLocal(exam.end_time),
    project_id: exam.project_id || '',
    reminder_15min: Number(exam.reminder_15min ?? 1),
    reminder_5min: Number(exam.reminder_5min ?? 1),
    reminder_start: Number(exam.reminder_start ?? 1)
  }
}

function resetForm() {
  form.value = defaultForm()
}

function handleClosed() {
  resetForm()
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true

  try {
    const submitData = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      start_time: form.value.start_time,
      end_time: form.value.end_time,
      project_id: form.value.project_id,
      reminder_15min: form.value.reminder_15min,
      reminder_5min: form.value.reminder_5min,
      reminder_start: form.value.reminder_start
    }

    if (isEdit.value) {
      await examStore.updateExam(props.exam.id, submitData)
      success('考试已更新')
    } else {
      await examStore.createExam(submitData)
      success('考试已创建')
    }

    visible.value = false
    emit('success')
  } catch (err) {
    ErrorHandler.handle(err, {
      fallbackMessage: isEdit.value ? '更新失败，请稍后重试' : '创建失败，请稍后重试'
    })
  } finally {
    submitting.value = false
  }
}

function disabledStartDate(time) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return time.getTime() < today.getTime()
}

function disabledEndDate(time) {
  if (!form.value.start_time) {
    return disabledStartDate(time)
  }
  const startTime = new Date(form.value.start_time)
  startTime.setHours(0, 0, 0, 0)
  return time.getTime() < startTime.getTime()
}

function formatDateTimeLocal(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
}
</script>

<style scoped>
.field-grid,
.time-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  column-gap: 12px;
}

:global(.exam-dialog-mask) {
  inset: 0 !important;
  background: rgba(15, 23, 42, 0.18) !important;
}

.reminder-panel {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.reminder-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid #dfe5ec;
  border-radius: 6px;
  background: #f8fafc;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.reminder-option:hover {
  border-color: #7aa2c9;
  background: #ffffff;
}

.reminder-option span {
  color: #1f2937;
  font-size: 14px;
  font-weight: 650;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .field-grid,
  .time-grid {
    grid-template-columns: 1fr;
  }

  .reminder-panel {
    grid-template-columns: 1fr;
  }
}
</style>
