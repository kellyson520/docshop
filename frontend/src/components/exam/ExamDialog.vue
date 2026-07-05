<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑考试' : '新增考试'"
    width="820px"
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
            placeholder="请输入考试名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="所属项目" prop="project_id">
          <el-select
            v-model="form.project_id"
            placeholder="请选择所属项目"
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
            placeholder="请选择开始时间"
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
            placeholder="请选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="disabledEndDate"
            style="width: 100%"
          />
        </el-form-item>
      </div>

      <el-form-item label="考试说明" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          placeholder="请输入考试说明、范围或注意事项"
          :rows="2"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="提醒时间">
        <div class="reminder-panel segmented-reminder-panel">
          <div class="reminder-panel__header">
            <div>
              <div class="reminder-title">分段提醒</div>
              <div class="reminder-subtitle">可自由组合多个提醒时间，系统会在考试开始前分段提醒。</div>
            </div>
            <el-button text type="primary" @click="resetDefaultReminders">恢复默认</el-button>
          </div>

          <div class="reminder-presets" aria-label="快捷提醒">
            <el-button
              v-for="preset in REMINDER_PRESETS"
              :key="preset.value"
              size="small"
              round
              :type="form.reminder_offsets_minutes.includes(preset.value) ? 'primary' : 'default'"
              @click="togglePresetReminder(preset.value)"
            >
              {{ preset.label }}
            </el-button>
          </div>

          <div class="reminder-custom-row">
            <el-input-number
              v-model="customReminder.value"
              :min="1"
              :max="reminderCustomMax"
              :step="1"
              controls-position="right"
              class="reminder-custom-number"
            />
            <el-select v-model="customReminder.unit" class="reminder-unit-select" aria-label="提醒单位">
              <el-option label="分钟" value="minutes" />
              <el-option label="小时" value="hours" />
              <el-option label="天" value="days" />
            </el-select>
            <el-button type="primary" plain @click="addCustomReminder">添加提醒</el-button>
          </div>

          <transition-group name="reminder-tag" tag="div" class="reminder-tags">
            <el-tag
              v-for="offset in form.reminder_offsets_minutes"
              :key="offset"
              closable
              effect="light"
              type="info"
              @close="removeReminderOffset(offset)"
            >
              {{ formatReminderOffset(offset) }}
            </el-tag>
          </transition-group>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存考试' : '创建考试' }}
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

const REMINDER_PRESETS = [
  { label: '5 分钟', value: 5 },
  { label: '10 分钟', value: 10 },
  { label: '15 分钟', value: 15 },
  { label: '30 分钟', value: 30 },
  { label: '1 小时', value: 60 },
  { label: '2 小时', value: 120 },
  { label: '1 天', value: 1440 },
  { label: '开始时', value: 0 }
]

const DEFAULT_REMINDER_OFFSETS = [15, 5, 0]
const REMINDER_MAX_DAYS = 365
const REMINDER_MAX_OFFSET_MINUTES = REMINDER_MAX_DAYS * 24 * 60

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
const customReminder = ref({ value: 30, unit: 'minutes' })
const reminderCustomMax = computed(() => {
  if (customReminder.value.unit === 'days') return REMINDER_MAX_DAYS
  if (customReminder.value.unit === 'hours') return REMINDER_MAX_DAYS * 24
  return REMINDER_MAX_OFFSET_MINUTES
})

const defaultForm = () => ({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  project_id: '',
  reminder_offsets_minutes: [...DEFAULT_REMINDER_OFFSETS],
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
    { min: 2, max: 100, message: '考试名称长度为 2-100 个字符', trigger: 'blur' }
  ],
  project_id: [
    { required: true, message: '请选择所属项目', trigger: 'change' }
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
    console.warn('[ExamDialog] 加载项目失败:', err)
  }
}

function fillForm(exam) {
  if (!exam) {
    resetForm()
    return
  }

  const offsets = Array.isArray(exam.reminder_offsets_minutes)
    ? exam.reminder_offsets_minutes
    : legacyReminderOffsets(exam)

  form.value = {
    name: exam.name || '',
    description: exam.description || '',
    start_time: formatDateTimeLocal(exam.start_time),
    end_time: formatDateTimeLocal(exam.end_time),
    project_id: exam.project_id || '',
    reminder_offsets_minutes: normalizeReminderOffsets(offsets),
    reminder_15min: Number(exam.reminder_15min ?? 1),
    reminder_5min: Number(exam.reminder_5min ?? 1),
    reminder_start: Number(exam.reminder_start ?? 1)
  }
}

function resetForm() {
  form.value = defaultForm()
  customReminder.value = { value: 30, unit: 'minutes' }
}

function handleClosed() {
  resetForm()
  formRef.value?.clearValidate()
}

function normalizeReminderOffsets(offsets) {
  return [...new Set((offsets || [])
    .map((offset) => Number(offset))
    .filter((offset) => Number.isFinite(offset) && offset >= 0 && offset <= REMINDER_MAX_OFFSET_MINUTES))]
    .sort((a, b) => b - a)
}

function legacyReminderOffsets(exam) {
  const offsets = []
  if (Number(exam?.reminder_15min ?? 1) === 1) offsets.push(15)
  if (Number(exam?.reminder_5min ?? 1) === 1) offsets.push(5)
  if (Number(exam?.reminder_start ?? 1) === 1) offsets.push(0)
  return offsets
}

function togglePresetReminder(offset) {
  const current = form.value.reminder_offsets_minutes
  if (current.includes(offset)) {
    removeReminderOffset(offset)
    return
  }
  form.value.reminder_offsets_minutes = normalizeReminderOffsets([...current, offset])
}

function addCustomReminder() {
  const value = Number(customReminder.value.value)
  if (!Number.isFinite(value) || value <= 0) return

  const multiplier = customReminder.value.unit === 'days'
    ? 1440
    : customReminder.value.unit === 'hours'
      ? 60
      : 1
  const offset = Math.min(Math.round(value * multiplier), REMINDER_MAX_OFFSET_MINUTES)
  form.value.reminder_offsets_minutes = normalizeReminderOffsets([
    ...form.value.reminder_offsets_minutes,
    offset
  ])
}

function removeReminderOffset(offset) {
  form.value.reminder_offsets_minutes = form.value.reminder_offsets_minutes.filter(item => item !== offset)
}

function resetDefaultReminders() {
  form.value.reminder_offsets_minutes = [...DEFAULT_REMINDER_OFFSETS]
}

function formatReminderOffset(offset) {
  if (offset === 0) return '开始时'
  if (offset % 1440 === 0) return `提前 ${offset / 1440} 天`
  if (offset % 60 === 0) return `提前 ${offset / 60} 小时`
  return `提前 ${offset} 分钟`
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
    form.value.reminder_offsets_minutes = normalizeReminderOffsets(form.value.reminder_offsets_minutes)
    const submitData = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      start_time: form.value.start_time,
      end_time: form.value.end_time,
      project_id: form.value.project_id,
      reminder_offsets_minutes: form.value.reminder_offsets_minutes,
      reminder_15min: form.value.reminder_offsets_minutes.includes(15) ? 1 : 0,
      reminder_5min: form.value.reminder_offsets_minutes.includes(5) ? 1 : 0,
      reminder_start: form.value.reminder_offsets_minutes.includes(0) ? 1 : 0
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
      fallbackMessage: isEdit.value ? '更新考试失败，请稍后重试' : '创建考试失败，请稍后重试'
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
}

.segmented-reminder-panel {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid #dfe7f1;
  border-radius: 12px;
  background:
    radial-gradient(circle at 12% 0%, rgba(56, 189, 248, 0.12), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.reminder-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.reminder-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 750;
}

.reminder-subtitle {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.reminder-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.reminder-custom-row {
  display: grid;
  grid-template-columns: 118px 104px auto;
  gap: 8px;
  align-items: center;
}

.reminder-custom-number,
.reminder-unit-select {
  width: 100%;
}

.reminder-tags {
  min-height: 34px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.reminder-tag-enter-active,
.reminder-tag-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.reminder-tag-enter-from,
.reminder-tag-leave-to {
  opacity: 0;
  transform: translate3d(0, -4px, 0) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .reminder-tag-enter-active,
  .reminder-tag-leave-active {
    transition-duration: 1ms;
  }
}

@media (max-width: 720px) {
  .field-grid,
  .time-grid,
  .reminder-custom-row {
    grid-template-columns: 1fr;
  }

  .reminder-panel__header {
    flex-direction: column;
  }
}
</style>
