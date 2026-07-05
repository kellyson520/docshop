<template>
  <div class="exam-public">
    <!-- 返回按钮 -->
    <el-button text class="back-btn" @click="$router.push('/')">
      <el-icon><ArrowLeft /></el-icon>
      返回首页
    </el-button>

    <!-- 加载 -->
    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载考试信息...</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="error-wrap">
      <el-icon :size="64" color="#F56C6C"><WarningFilled /></el-icon>
      <h2>加载失败</h2>
      <p>{{ error }}</p>
      <el-button @click="fetchExam">重试</el-button>
      <el-button @click="$router.push('/')">返回首页</el-button>
    </div>

    <!-- 内容 -->
    <template v-else-if="exam">
      <!-- 顶部信息条 -->
      <div class="exam-hero">
        <div class="hero-left">
          <h1 class="hero-name">{{ exam.name }}</h1>
          <div class="hero-meta">
            <span class="hero-time">
              <el-icon><Clock /></el-icon>
              {{ fmt(exam.start_time) }} — {{ fmt(exam.end_time) }}
            </span>
            <el-tag :type="statusType" effect="dark" size="small">{{ statusText }}</el-tag>
          </div>
          <div v-if="exam.description" class="hero-desc">{{ exam.description }}</div>
        </div>
        <div class="hero-right">
          <el-button-group>
            <el-button :type="view === 'timeline' ? 'primary' : ''" @click="view = 'timeline'">
              <el-icon><List /></el-icon> 时间线
            </el-button>
            <el-button :type="view === 'calendar' ? 'primary' : ''" @click="view = 'calendar'">
              <el-icon><Calendar /></el-icon> 日历
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- 进度指示条 -->
      <div class="progress-strip">
        <div class="strip-bar">
          <div
            class="strip-fill"
            :class="exam.status"
            :style="{ width: progressPercent + '%' }"
          ></div>
          <div class="strip-now" v-if="exam.status === 'ongoing'" :style="{ left: progressPercent + '%' }"></div>
        </div>
        <div class="strip-labels">
          <span class="strip-start">{{ fmtShort(exam.start_time) }}</span>
          <span class="strip-end">{{ fmtShort(exam.end_time) }}</span>
        </div>
      </div>

      <!-- 时间线视图 -->
      <div v-if="view === 'timeline'" class="timeline-panel">
        <div class="tl-header">
          <span class="tl-title">考试时间线</span>
          <span class="tl-desc">精度到分钟 · 按时间顺序排列</span>
        </div>
        <div class="tl-track">
          <div class="tl-item" :class="exam.status">
            <!-- 时间列 -->
            <div class="tl-time">
              <div class="tl-time-start">{{ timeStr(exam.start_time) }}</div>
              <div class="tl-time-dot" :class="exam.status"><span></span></div>
              <div class="tl-time-end">{{ timeStr(exam.end_time) }}</div>
            </div>
            <!-- 内容列 -->
            <div class="tl-card" :class="exam.status">
              <div class="tl-card-head">
                <span class="tl-card-name">{{ exam.name }}</span>
                <el-tag :type="statusType" size="small" effect="plain">{{ statusText }}</el-tag>
              </div>
              <div class="tl-card-body">
                <div class="tl-card-row">
                  <span class="tl-label">日期</span>
                  <span class="tl-val">{{ fmtDate(exam.start_time) }}</span>
                </div>
                <div class="tl-card-row">
                  <span class="tl-label">时间</span>
                  <span class="tl-val">{{ timeStr(exam.start_time) }} — {{ timeStr(exam.end_time) }}</span>
                </div>
                <div class="tl-card-row">
                  <span class="tl-label">时长</span>
                  <span class="tl-val">{{ duration }}</span>
                </div>
                <div class="tl-card-row" v-if="exam.description">
                  <span class="tl-label">说明</span>
                  <span class="tl-val desc">{{ exam.description }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 日历视图 -->
      <div v-else class="calendar-panel">
        <div class="cal-header">
          <el-button text @click="prevMonth"><el-icon><ArrowLeft /></el-icon></el-button>
          <span class="cal-title">{{ calYear }} 年 {{ calMonth + 1 }} 月</span>
          <el-button text @click="nextMonth"><el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="cal-grid">
          <div class="cal-weekday" v-for="d in weekdays" :key="d">{{ d }}</div>
          <div
            v-for="(day, idx) in calDays"
            :key="idx"
            class="cal-day"
            :class="{
              'is-today': day.isToday,
              'is-exam': day.isExam,
              'is-other-month': !day.inMonth,
            }"
          >
            <span class="cal-day-num">{{ day.num }}</span>
            <div v-if="day.isExam" class="cal-event" :class="exam.status">
              {{ exam.name }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Calendar, List, ArrowLeft, ArrowRight, Loading, WarningFilled } from '@element-plus/icons-vue'
import { get } from '@/api/client'

defineOptions({ name: 'PublicExamView' })

const route = useRoute()
const router = useRouter()

const exam = ref(null)
const loading = ref(true)
const error = ref('')
const view = ref('timeline') // timeline | calendar
const calMonth = ref(new Date().getMonth())
const calYear = ref(new Date().getFullYear())

const weekdays = ['一', '二', '三', '四', '五', '六', '日']

// ── 状态 ──
const statusType = computed(() => {
  const m = { upcoming: 'primary', ongoing: 'success', expired: 'info' }
  return m[exam.value?.status] || 'info'
})
const statusText = computed(() => {
  const m = { upcoming: '即将开始', ongoing: '进行中', expired: '已结束' }
  return m[exam.value?.status] || exam.value?.status || ''
})

const progressPercent = computed(() => {
  if (!exam.value) return 0
  const s = new Date(exam.value.start_time).getTime()
  const e = new Date(exam.value.end_time).getTime()
  const n = Date.now()
  if (n <= s) return 0
  if (n >= e) return 100
  return Math.round(((n - s) / (e - s)) * 100)
})

const duration = computed(() => {
  if (!exam.value) return ''
  const ms = new Date(exam.value.end_time) - new Date(exam.value.start_time)
  const mins = Math.round(ms / 60000)
  if (mins < 60) return `${mins} 分钟`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h} 小时 ${m} 分钟` : `${h} 小时`
})

// ── 日历导航 ──
function prevMonth() {
  const prev = new Date(calYear.value, calMonth.value - 1, 1)
  calYear.value = prev.getFullYear()
  calMonth.value = prev.getMonth()
}

function nextMonth() {
  const next = new Date(calYear.value, calMonth.value + 1, 1)
  calYear.value = next.getFullYear()
  calMonth.value = next.getMonth()
}

// ── 日历 ──
const calDays = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const firstDay = new Date(y, m, 1)
  const lastDay = new Date(y, m + 1, 0)
  const startOffset = (firstDay.getDay() + 6) % 7 // Mon=0
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, '0')}-${today.getDate().toString().padStart(2, '0')}`

  const ex = exam.value
  const examStart = ex ? new Date(ex.start_time) : null
  const examEnd = ex ? new Date(ex.end_time) : null
  const examStartDay = examStart ? `${examStart.getFullYear()}-${(examStart.getMonth() + 1).toString().padStart(2, '0')}-${examStart.getDate().toString().padStart(2, '0')}` : ''
  const examEndDay = examEnd ? `${examEnd.getFullYear()}-${(examEnd.getMonth() + 1).toString().padStart(2, '0')}-${examEnd.getDate().toString().padStart(2, '0')}` : ''

  const days = []
  // 上个月的填充
  for (let i = startOffset - 1; i >= 0; i--) {
    const d = new Date(y, m, -i)
    days.push({ num: d.getDate(), inMonth: false, isToday: false, isExam: false })
  }
  // 本月
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const ds = `${y}-${(m + 1).toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`
    days.push({
      num: d,
      inMonth: true,
      isToday: ds === todayStr,
      isExam: ex && ds >= examStartDay && ds <= examEndDay,
    })
  }
  // 下个月填充
  const remaining = 7 - (days.length % 7)
  if (remaining < 7) {
    for (let d = 1; d <= remaining; d++) {
      days.push({ num: d, inMonth: false, isToday: false, isExam: false })
    }
  }
  return days
})

// ── 格式化 ──
function fmt(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
function fmtShort(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
}
function timeStr(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

// ── 数据 ──
async function fetchExam() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const data = await get(`/share/public-exams/${id}`)
    exam.value = data
    // 日历跳到考试月
    const d = new Date(data.start_time)
    calMonth.value = d.getMonth()
    calYear.value = d.getFullYear()
  } catch {
    error.value = '考试不存在或加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => fetchExam())
</script>

<style scoped>
.exam-public {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  min-height: 100vh;
  font-family: system-ui, sans-serif;
}
.back-btn {
  margin-bottom: 16px;
  color: #909399;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 6px;
}
.back-btn:hover {
  color: #6366f1;
  background: #f0f0ff;
}
.loading-wrap, .error-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 12px;
  color: #909399;
}
.error-wrap h2 { margin: 8px 0; color: #303133; }
.error-wrap p { color: #909399; }

/* hero */
.exam-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #eee;
  margin-bottom: 16px;
}
.hero-name { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: #1e293b; }
.hero-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #64748b; margin-bottom: 8px; }
.hero-meta .el-icon { margin-right: 2px; vertical-align: -1px; }
.hero-desc { font-size: 13px; color: #94a3b8; line-height: 1.5; }

/* progress strip */
.progress-strip { margin-bottom: 20px; }
.strip-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  position: relative;
  overflow: visible;
}
.strip-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 60s linear;
}
.strip-fill.upcoming { background: #6366f1; }
.strip-fill.ongoing { background: #22c55e; }
.strip-fill.expired { background: #94a3b8; }
.strip-now {
  position: absolute;
  top: -3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #22c55e;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #22c55e44;
  transform: translateX(-50%);
}
.strip-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
}

/* ── 时间线 ── */
.timeline-panel { margin-top: 8px; }
.tl-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
.tl-title { font-size: 15px; font-weight: 600; color: #334155; }
.tl-desc { font-size: 12px; color: #94a3b8; }
.tl-track { position: relative; }
.tl-item { display: flex; gap: 20px; position: relative; }
.tl-time { width: 70px; display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0; }
.tl-time-start, .tl-time-end { font-size: 12px; color: #94a3b8; }
.tl-time-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; position: relative; }
.tl-time-dot span {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #cbd5e1;
}
.tl-time-dot.upcoming span { background: #6366f1; box-shadow: 0 0 0 3px #6366f122; }
.tl-time-dot.ongoing span { background: #22c55e; box-shadow: 0 0 0 3px #22c55e22; }
.tl-time-dot.expired span { background: #94a3b8; }
/* 竖线 */
.tl-item::before {
  content: '';
  position: absolute;
  top: 28px;
  bottom: 0;
  left: 35px;
  width: 2px;
  background: #e2e8f0;
}
.tl-card {
  flex: 1;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.tl-card.upcoming { border-left: 3px solid #6366f1; }
.tl-card.ongoing { border-left: 3px solid #22c55e; background: #f0fdf4; }
.tl-card.expired { border-left: 3px solid #cbd5e1; background: #f8fafc; }
.tl-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tl-card-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.tl-card-row { display: flex; gap: 12px; margin-bottom: 6px; font-size: 13px; }
.tl-label { color: #94a3b8; min-width: 36px; }
.tl-val { color: #475569; }
.tl-val.desc { color: #64748b; line-height: 1.5; }

/* ── 日历 ── */
.calendar-panel { margin-top: 8px; background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 20px; }
.cal-header { display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 16px; }
.cal-title { font-size: 16px; font-weight: 600; color: #334155; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.cal-weekday {
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  padding: 6px 0;
}
.cal-day {
  aspect-ratio: 1;
  padding: 4px;
  border-radius: 6px;
  font-size: 12px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
}
.cal-day.is-other-month { opacity: 0.35; }
.cal-day.is-today { background: #eef2ff; }
.cal-day.is-exam { background: #f0fdf4; }
.cal-day-num { font-weight: 600; color: #475569; margin-bottom: 2px; }
.cal-day.is-today .cal-day-num { color: #6366f1; }
.cal-event {
  font-size: 10px;
  color: #fff;
  border-radius: 3px;
  padding: 1px 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.cal-event.upcoming { background: #6366f1; }
.cal-event.ongoing { background: #22c55e; }
.cal-event.expired { background: #94a3b8; }

@media (max-width: 640px) {
  .exam-hero { flex-direction: column; }
  .tl-item { gap: 12px; }
  .tl-time { width: 56px; }
}
</style>
