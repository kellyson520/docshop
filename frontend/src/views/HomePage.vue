<template>
  <div class="store-page">
    <header class="store-topbar">
      <router-link to="/" class="brand" aria-label="DocDist home">
        <span class="brand-mark">
          <el-icon :size="22"><DocumentChecked /></el-icon>
        </span>
        <span class="brand-copy">
          <strong>DocDist</strong>
          <small>Document Store</small>
        </span>
      </router-link>

      <div class="topbar-actions">
        <el-input
          v-model="keyword"
          placeholder="搜索文档、课程、项目"
          :prefix-icon="Search"
          clearable
          class="topbar-search"
          @input="onSearch"
        />
        <el-button v-if="isLoggedIn" type="primary" @click="$router.push('/admin')">后台</el-button>
        <el-button v-else @click="$router.push('/login')">登录</el-button>
      </div>
    </header>

    <AnnouncementBar />

    <main class="store-shell">
      <section class="catalog-head">
        <div class="headline">
          <span class="eyebrow">Public catalog</span>
          <h1>资料商店</h1>
          <p>按格式浏览公开发布的文档、表格和试卷资料。</p>
        </div>

        <div class="head-stats" aria-label="catalog statistics">
          <div class="stat-tile">
            <strong>{{ total }}</strong>
            <span>公开项目</span>
          </div>
          <div class="stat-tile">
            <strong>{{ visibleProjects.length }}</strong>
            <span>当前显示</span>
          </div>
          <div class="stat-tile accent">
            <strong>{{ exams.length }}</strong>
            <span>近期考试</span>
          </div>
        </div>
      </section>

      <section v-if="exams.length" class="exam-strip" aria-label="upcoming exams">
        <button
          v-for="exam in exams"
          :key="exam.id"
          class="exam-pill"
          type="button"
          @click="openExam(exam.id)"
        >
          <span>{{ exam.name }}</span>
          <small>{{ formatDate(exam.start_time) }}</small>
        </button>
      </section>

      <section class="catalog-tools">
        <div class="filter-tabs" aria-label="file type filters">
          <button
            v-for="cat in categories"
            :key="cat.value"
            type="button"
            :class="['filter-chip', { active: activeCategory === cat.value }]"
            @click="setCategory(cat.value)"
          >
            <span class="chip-dot" :class="cat.value || 'all'"></span>
            {{ cat.label }}
          </button>
        </div>
        <span class="result-count">{{ resultLabel }}</span>
      </section>

      <section v-loading="loading" class="catalog-grid" aria-live="polite">
        <article
          v-for="(project, index) in visibleProjects"
          :key="project.id"
          class="project-card"
          :style="{ '--delay': `${Math.min(index * 45, 360)}ms` }"
          @click="openProject(project.share_token)"
        >
          <div class="cover" :class="fileType(project)">
            <img v-if="resolveCoverUrl(project.cover_image)" :src="resolveCoverUrl(project.cover_image)" alt="" />
            <div v-else class="cover-fallback">
              <el-icon :size="44">
                <Document v-if="isDoc(project)" />
                <Grid v-else-if="isSheet(project)" />
                <Picture v-else-if="isPdf(project)" />
                <Folder v-else />
              </el-icon>
              <span>{{ fileType(project).toUpperCase() }}</span>
            </div>
          </div>

          <div class="card-body">
            <div class="card-meta">
              <el-tag size="small" :type="tagType(fileType(project))" effect="plain">
                {{ fileType(project).toUpperCase() }}
              </el-tag>
              <span>{{ project.file_count || 0 }} 文件</span>
            </div>
            <h2>{{ project.name }}</h2>
            <p>{{ project.description || '暂无描述' }}</p>
            <div class="uploader-line">
              <el-avatar
                :size="24"
                :src="project.uploader?.avatar || ''"
                class="uploader-avatar"
              >
                {{ uploaderInitial(project) }}
              </el-avatar>
              <div class="uploader-copy">
                <span>{{ project.uploader?.username || '未知上传者' }}</span>
                <small>{{ roleLabel(project.uploader?.role) }}</small>
              </div>
            </div>
            <div class="card-foot">
              <span>{{ formatDate(project.updated_at || project.created_at) }}</span>
              <span class="open-link">打开</span>
            </div>
          </div>
        </article>
      </section>

      <el-empty
        v-if="!loading && !visibleProjects.length"
        description="暂无公开文档"
        class="empty-state"
      />

      <div v-if="total > pageSize && !activeCategory" class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          background
          @current-change="fetchProjects"
        />
      </div>
    </main>

    <footer class="store-foot">
      <span>DocDist</span>
      <span>公开资料分发</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DocumentChecked, Search, Document, Grid, Picture, Folder } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { formatDate } from '@/utils'
import { resolveCoverUrl } from '@/utils/cover'
import AnnouncementBar from '@/components/common/AnnouncementBar.vue'

const router = useRouter()
const isLoggedIn = computed(() => !!localStorage.getItem('access_token'))

const projects = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 24
const total = ref(0)
const keyword = ref('')
const activeCategory = ref('')
const exams = ref([])
let timer = null

const categories = [
  { label: '全部', value: '' },
  { label: 'DOCX', value: 'docx' },
  { label: 'PDF', value: 'pdf' },
  { label: 'XLSX', value: 'xlsx' }
]

const visibleProjects = computed(() => {
  if (!activeCategory.value) return projects.value
  return projects.value.filter(project => fileType(project) === activeCategory.value)
})

const resultLabel = computed(() => {
  const suffix = activeCategory.value ? `${activeCategory.value.toUpperCase()} ` : ''
  return `${suffix}${visibleProjects.value.length} / ${total.value} 个项目`
})

function normalizedType(value) {
  return String(value || 'file').toLowerCase()
}

function fileType(project) {
  return normalizedType(project.first_file?.file_type)
}

function isDoc(project) {
  return ['doc', 'docx'].includes(fileType(project))
}

function isSheet(project) {
  return ['xls', 'xlsx'].includes(fileType(project))
}

function isPdf(project) {
  return fileType(project) === 'pdf'
}

function tagType(type) {
  return { docx: '', doc: '', xlsx: 'success', xls: 'success', pdf: 'danger' }[type] || 'info'
}

function roleLabel(role) {
  return { admin: '管理员', user: '上传者', viewer: '访客' }[role] || '上传者'
}

function uploaderInitial(project) {
  return (project.uploader?.username || '?').charAt(0).toUpperCase()
}

async function fetchExams() {
  try {
    exams.value = await get('/share/public-exams')
  } catch {
    exams.value = []
  }
}

async function fetchProjects() {
  loading.value = true
  try {
    const data = await get('/share/public-projects', {
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined
    })
    projects.value = data.items || []
    total.value = data.total || 0
  } catch {
    projects.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    page.value = 1
    fetchProjects()
  }, 260)
}

function setCategory(value) {
  activeCategory.value = activeCategory.value === value ? '' : value
}

function openProject(token) {
  router.push(`/s/${token}`)
}

function openExam(id) {
  router.push(`/exam/${id}`)
}

onMounted(() => {
  fetchProjects()
  fetchExams()
})
</script>

<style scoped>
.store-page {
  min-height: 100vh;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.13), transparent 38%),
    linear-gradient(315deg, rgba(217, 93, 57, 0.1), transparent 42%),
    linear-gradient(90deg, rgba(23, 33, 31, 0.05) 1px, transparent 1px),
    linear-gradient(180deg, #eef3ec 0%, #f7f5ef 46%, #f3f6f5 100%);
  background-size: 100% 520px, 100% 620px, 28px 28px, 100% 100%;
  color: #17211f;
  display: flex;
  flex-direction: column;
}

.store-topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 28px;
  background: rgba(247, 245, 239, 0.92);
  border-bottom: 1px solid rgba(23, 33, 31, 0.12);
  backdrop-filter: blur(14px);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #17211f;
  text-decoration: none;
  min-width: 0;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #0f766e;
  color: #fffdf6;
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.22);
}

.brand-copy {
  display: grid;
  line-height: 1.05;
}

.brand-copy strong {
  font-size: 18px;
}

.brand-copy small {
  margin-top: 4px;
  font-size: 11px;
  color: #68746d;
}

.topbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.topbar-search {
  width: min(360px, 40vw);
}

.store-shell {
  width: min(1380px, calc(100% - 40px));
  margin: 0 auto;
  flex: 1;
  padding: 28px 0 44px;
}

.catalog-head {
  min-height: 180px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 28px;
  align-items: end;
  padding: 34px;
  border: 1px solid rgba(23, 33, 31, 0.14);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.94), rgba(23, 33, 31, 0.96)),
    linear-gradient(45deg, transparent 0 48%, rgba(255, 255, 255, 0.1) 48% 52%, transparent 52%);
  color: #fffdf6;
  overflow: hidden;
  animation: panel-in 360ms ease both;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
  color: #ffd166;
  text-transform: uppercase;
}

.headline h1 {
  margin: 0;
  font-size: 42px;
  line-height: 1;
  font-weight: 800;
}

.headline p {
  max-width: 520px;
  margin: 14px 0 0;
  font-size: 15px;
  line-height: 1.7;
  color: rgba(255, 253, 246, 0.78);
}

.head-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 10px;
}

.stat-tile {
  min-width: 96px;
  padding: 14px;
  border-radius: 8px;
  background: rgba(255, 253, 246, 0.1);
  border: 1px solid rgba(255, 253, 246, 0.18);
}

.stat-tile strong {
  display: block;
  font-size: 28px;
  line-height: 1;
}

.stat-tile span {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 253, 246, 0.72);
}

.stat-tile.accent {
  background: rgba(255, 209, 102, 0.16);
}

.exam-strip {
  margin-top: 14px;
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.exam-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 8px 14px;
  border: 1px solid rgba(201, 138, 42, 0.28);
  border-radius: 8px;
  background: #fff6df;
  color: #7a5015;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 160ms ease, border-color 160ms ease;
}

.exam-pill:hover {
  transform: translateY(-2px);
  border-color: #c98a2a;
}

.exam-pill span {
  font-weight: 700;
}

.exam-pill small {
  color: #9b6d25;
}

.catalog-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding: 12px 2px;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-chip {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 13px;
  border: 1px solid rgba(23, 33, 31, 0.14);
  border-radius: 8px;
  background: rgba(255, 253, 246, 0.76);
  color: #2d3834;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease, transform 160ms ease;
}

.filter-chip:hover,
.filter-chip.active {
  background: #17211f;
  color: #fffdf6;
  transform: translateY(-1px);
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 99px;
  background: #68746d;
}

.chip-dot.docx {
  background: #2f80ed;
}

.chip-dot.pdf {
  background: #d95d39;
}

.chip-dot.xlsx {
  background: #0f9f6e;
}

.chip-dot.all {
  background: #c98a2a;
}

.result-count {
  font-size: 13px;
  color: #68746d;
  white-space: nowrap;
}

.catalog-grid {
  min-height: 380px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 14px;
  padding: 14px;
  border: 1px solid rgba(23, 33, 31, 0.1);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(255, 253, 246, 0.64)),
    linear-gradient(90deg, rgba(255, 253, 246, 0.5) 1px, transparent 1px);
  background-size: 100% 100%, 34px 34px;
}

.project-card {
  border: 1px solid rgba(23, 33, 31, 0.12);
  border-radius: 8px;
  background: rgba(255, 253, 246, 0.9);
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 14px 34px rgba(23, 33, 31, 0.08);
  animation: card-in 360ms ease both;
  animation-delay: var(--delay);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.project-card:hover {
  transform: translateY(-5px);
  border-color: rgba(15, 118, 110, 0.42);
  box-shadow: 0 22px 48px rgba(23, 33, 31, 0.14);
}

.cover {
  height: 132px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: #e6ece9;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: #fffdf6;
}

.cover-fallback span {
  font-size: 12px;
  font-weight: 800;
}

.cover.doc,
.cover.docx {
  background: linear-gradient(135deg, #2457a6, #2f80ed);
}

.cover.pdf {
  background: linear-gradient(135deg, #9f2f22, #d95d39);
}

.cover.xls,
.cover.xlsx {
  background: linear-gradient(135deg, #0b6b4a, #0f9f6e);
}

.cover.file {
  background: linear-gradient(135deg, #42534e, #7c8b83);
}

.card-body {
  padding: 13px 14px 14px;
}

.card-meta,
.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-meta span,
.card-foot span {
  font-size: 12px;
  color: #68746d;
}

.card-body h2 {
  min-height: 38px;
  margin: 9px 0 6px;
  font-size: 16px;
  line-height: 1.2;
  color: #17211f;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-body p {
  min-height: 32px;
  margin: 0 0 9px;
  font-size: 13px;
  line-height: 1.4;
  color: #68746d;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.uploader-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  margin-bottom: 10px;
  padding: 5px 7px;
  border: 1px solid rgba(23, 33, 31, 0.08);
  border-radius: 8px;
  background: rgba(247, 245, 239, 0.68);
}

.uploader-avatar {
  flex: 0 0 auto;
  background: #dfe8e4;
  color: #42534e;
  font-size: 12px;
  font-weight: 800;
}

.uploader-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.uploader-copy span {
  overflow: hidden;
  color: #26312d;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploader-copy small {
  color: #7a867e;
  font-size: 11px;
  line-height: 1.1;
}

.open-link {
  color: #0f766e !important;
  font-weight: 800;
}

.empty-state {
  margin: 28px 0 12px;
  border-radius: 8px;
  background: rgba(255, 253, 246, 0.76);
  border: 1px solid rgba(23, 33, 31, 0.1);
}

.pager {
  display: flex;
  justify-content: center;
  padding: 28px 0 0;
}

.store-foot {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 28px;
  border-top: 1px solid rgba(23, 33, 31, 0.12);
  color: #68746d;
  font-size: 12px;
}

@keyframes panel-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .catalog-head,
  .project-card {
    animation: none;
  }

  .project-card,
  .filter-chip,
  .exam-pill {
    transition: none;
  }
}

@media (max-width: 860px) {
  .store-topbar {
    height: auto;
    align-items: stretch;
    flex-direction: column;
    padding: 12px 16px;
  }

  .topbar-actions {
    width: 100%;
  }

  .topbar-search {
    flex: 1;
    width: auto;
  }

  .store-shell {
    width: min(100% - 24px, 1380px);
    padding-top: 16px;
  }

  .catalog-head {
    grid-template-columns: 1fr;
    align-items: start;
    padding: 24px;
  }

  .headline h1 {
    font-size: 34px;
  }

  .head-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .catalog-tools {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 560px) {
  .brand-copy small {
    display: none;
  }

  .topbar-actions {
    flex-wrap: wrap;
  }

  .topbar-actions .el-button {
    flex: 0 0 auto;
  }

  .catalog-head {
    min-height: auto;
  }

  .head-stats {
    grid-template-columns: 1fr;
  }

  .catalog-grid {
    grid-template-columns: 1fr;
  }

  .store-foot {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .store-topbar {
    gap: 10px;
    padding: 10px 12px;
    box-shadow: 0 8px 22px rgba(23, 33, 31, 0.08);
  }

  .brand {
    justify-content: center;
  }

  .brand-mark {
    width: 34px;
    height: 34px;
  }

  .brand-copy strong {
    font-size: 17px;
  }

  .topbar-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .topbar-actions :deep(.el-button) {
    min-width: 72px;
    padding-inline: 12px;
  }

  .topbar-search {
    width: 100%;
  }

  .store-shell {
    width: calc(100% - 16px);
    padding: 10px 0 28px;
  }

  .catalog-head {
    gap: 18px;
    padding: 18px;
    border-radius: 16px;
  }

  .eyebrow {
    margin-bottom: 8px;
    font-size: 11px;
  }

  .headline h1 {
    font-size: 30px;
  }

  .headline p {
    margin-top: 10px;
    font-size: 13px;
    line-height: 1.55;
  }

  .head-stats {
    display: flex;
    grid-template-columns: none;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 2px;
    scroll-snap-type: x proximity;
    scrollbar-width: none;
  }

  .head-stats::-webkit-scrollbar {
    display: none;
  }

  .stat-tile {
    flex: 1 0 104px;
    min-width: 104px;
    padding: 10px;
    scroll-snap-align: start;
  }

  .stat-tile strong {
    font-size: 22px;
  }

  .stat-tile span {
    margin-top: 6px;
  }

  .exam-strip {
    margin-top: 10px;
    padding-bottom: 6px;
  }

  .exam-pill {
    min-height: 38px;
    padding: 7px 10px;
    font-size: 12px;
  }

  .catalog-tools {
    gap: 8px;
    margin-top: 10px;
    padding: 10px 0;
  }

  .filter-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 1px 0 4px;
    scrollbar-width: none;
  }

  .filter-tabs::-webkit-scrollbar {
    display: none;
  }

  .filter-chip {
    min-height: 32px;
    padding: 0 12px;
  }

  .result-count {
    width: 100%;
    padding-left: 4px;
  }

  .catalog-grid {
    min-height: 220px;
    gap: 10px;
    padding: 8px;
    border-radius: 16px;
  }

  .project-card {
    border-radius: 12px;
    box-shadow: 0 10px 26px rgba(23, 33, 31, 0.08);
  }

  .cover {
    height: 112px;
  }

  .card-body {
    padding: 11px 12px 12px;
  }

  .card-body h2 {
    min-height: auto;
    font-size: 15px;
  }

  .card-body p {
    min-height: auto;
    -webkit-line-clamp: 1;
  }

  .uploader-line {
    min-height: 30px;
    margin-bottom: 8px;
    padding: 5px;
  }

  .pager {
    padding-top: 16px;
  }

  .store-foot {
    gap: 6px;
    padding: 14px;
  }
}

@media (max-width: 390px) {
  .topbar-actions {
    grid-template-columns: 1fr;
  }

  .topbar-actions :deep(.el-button) {
    width: 100%;
  }
}
</style>
