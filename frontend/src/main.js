import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import router from './router'
import { useUiStore } from '@/stores/ui'
import App from './App.vue'
import './style.css'
import { initTracking } from '@/utils/trackingClient'

// 导入全局通用组件
import AppNavbar from '@/components/common/AppNavbar.vue'
import AppFooter from '@/components/common/AppFooter.vue'

const app = createApp(App)

// 按需导入实际使用的 Element Plus 图标
import {
  Plus,
  Delete,
  Edit,
  Search,
  Download,
  Upload,
  View,
  Refresh,
  Close,
  Check,
  ArrowLeft,
  ArrowRight,
  ArrowDown,
  Document,
  FolderOpened,
  Setting,
  User,
  UserFilled,
  Lock,
  Warning,
  InfoFilled,
  SuccessFilled,
  CircleCloseFilled,
  Expand,
  Fold,
  FullScreen,
  Menu as IconMenu,
  MoreFilled,
  Sort,
  Filter,
  Star,
  StarFilled,
  Link,
  CopyDocument,
  Timer,
  Histogram,
  DataLine,
  Loading,
  Sunny,
  Moon,
  Message,
  Phone,
  Location,
  Files,
  Clock,
  Folder,
  Hide,
  DocumentChecked,
  Monitor
} from '@element-plus/icons-vue'

// 注册按需导入的图标组件
const icons = {
  Plus,
  Delete,
  Edit,
  Search,
  Download,
  Upload,
  View,
  Refresh,
  Close,
  Check,
  ArrowLeft,
  ArrowRight,
  ArrowDown,
  Document,
  FolderOpened,
  Setting,
  User,
  UserFilled,
  Lock,
  Warning,
  InfoFilled,
  SuccessFilled,
  CircleCloseFilled,
  Expand,
  Fold,
  FullScreen,
  Menu: IconMenu,
  MoreFilled,
  Sort,
  Filter,
  Star,
  StarFilled,
  Link,
  CopyDocument,
  Timer,
  Histogram,
  DataLine,
  Loading,
  Sunny,
  Moon,
  Message,
  Phone,
  Location,
  Files,
  Clock,
  Folder,
  Hide,
  DocumentChecked,
  Monitor
}

for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

// 注册全局组件
app.component('AppNavbar', AppNavbar)
app.component('AppFooter', AppFooter)

// 全局错误处理器
app.config.errorHandler = (err, instance, info) => {
  // 开发环境打印详细错误信息
  if (import.meta.env.DEV) {
    console.error('[Global Error Handler]')
    console.error('错误信息:', err)
    console.error('组件实例:', instance)
    console.error('错误来源:', info)
  }

  // 避免在开发环境重复打印（Vue 会自动打印）
  // 生产环境可以接入错误上报服务
  // TODO: 接入 Sentry 或其他错误监控服务
}

// 初始化 Pinia
const pinia = createPinia()

// 初始化主题（在 Pinia 创建后、挂载前应用持久化的主题）
app.use(pinia)

// 应用已持久化的暗色模式主题
const uiStore = useUiStore()
uiStore.initTheme()

app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initTracking(), { once: true })
} else {
  initTracking()
}
