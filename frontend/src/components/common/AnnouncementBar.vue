<template>
  <!-- 滚动公告 -->
  <div v-if="scrollItems.length" class="announce-scroll">
    <div class="scroll-inner">
      <span v-for="(a, i) in scrollItems" :key="i" class="scroll-item">
        📢 {{ a.title }}：{{ a.content }}
        <span class="scroll-sep">|</span>
      </span>
    </div>
  </div>

  <!-- 弹窗公告 -->
  <el-dialog v-model="popupVisible" :title="popupItem?.title" width="420px" :close-on-click-modal="false">
    <p style="white-space:pre-wrap">{{ popupItem?.content }}</p>
    <template #footer><el-button type="primary" @click="popupVisible = false">知道了</el-button></template>
  </el-dialog>

  <!-- 侧边公告 → 右下角 Toast -->
  <div v-if="sidebarVisible" class="announce-toast">
    <div class="toast-header">
      <strong>{{ sidebarItems[0]?.title }}</strong>
      <el-button text :icon="Close" size="small" @click="sidebarVisible = false" />
    </div>
    <p class="toast-body">{{ sidebarItems[0]?.content }}</p>
  </div>

  <!-- 底部公告 -->
  <div v-if="bottomItems.length" class="announce-bottom">
    <span v-for="(a, i) in bottomItems" :key="a.id" class="bottom-item">
      {{ a.title }}：{{ a.content }}
      <span v-if="i < bottomItems.length - 1" class="bottom-sep">|</span>
    </span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { get } from '@/api/client'

const all = ref([])
const popupVisible = ref(false)
const popupItem = ref(null)
const sidebarVisible = ref(false)

const scrollItems = computed(() => all.value.filter(a => a.display_mode === 'scroll'))
const sidebarItems = computed(() => all.value.filter(a => a.display_mode === 'sidebar'))
const bottomItems = computed(() => all.value.filter(a => a.display_mode === 'bottom'))

async function fetchAnnouncements() {
  try { all.value = await get('/announcements/active') } catch { all.value = [] }
  // 弹窗：取第一个 popup 模式公告
  const popup = all.value.find(a => a.display_mode === 'popup')
  // 侧边 Toast
  const sidebar = all.value.find(a => a.display_mode === 'sidebar')
  if (sidebar) sidebarVisible.value = true
  if (popup) {
    const dismissed = sessionStorage.getItem(`ann_popup_${popup.id}`)
    if (!dismissed) {
      popupItem.value = popup
      popupVisible.value = true
      sessionStorage.setItem(`ann_popup_${popup.id}`, '1')
    }
  }
}

onMounted(fetchAnnouncements)
</script>

<style scoped>
.announce-scroll {
  background: linear-gradient(90deg, #fff7ed, #fef3c7);
  border-bottom: 1px solid #fde68a;
  overflow: hidden; white-space: nowrap; padding: 8px 0;
}
.scroll-inner { display: inline-block; animation: scroll-left 30s linear infinite; }
.scroll-item { font-size: 14px; color: #92400e; margin-right: 40px; }
.scroll-sep { color: #d97706; margin-left: 20px; }
@keyframes scroll-left { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }

.announce-toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 1000;
  width: 320px; background: #fff; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,.12); border: 1px solid #e5e7eb;
  padding: 16px; animation: toast-in .3s ease;
}
.toast-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.toast-header strong { font-size: 14px; color: #1f2937; }
.toast-body { font-size: 13px; color: #6b7280; margin: 0; line-height: 1.5; }
@keyframes toast-in { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

.announce-bottom {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 500;
  background: #1e293b; color: #e2e8f0; text-align: center;
  padding: 10px 20px; font-size: 14px;
}
.bottom-sep { margin: 0 16px; color: #475569; }
</style>
