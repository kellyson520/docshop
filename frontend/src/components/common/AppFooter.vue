<template>
  <footer class="app-footer" :class="{ 'app-footer--dark': isDark }">
    <div class="footer-container">
      <!-- 主要内容区 -->
      <div class="footer-content">
        <!-- Logo 和简介 -->
        <div class="footer-section footer-brand">
          <div class="brand-logo">
            <el-icon :size="28" class="logo-icon"><Document /></el-icon>
            <span class="brand-name">DocDist</span>
          </div>
          <p class="brand-desc">
            智能文档版本管理系统，帮助团队高效管理文档变更，追踪版本历史，提升协作效率。
          </p>
          <!-- 社交媒体图标 -->
          <div class="social-links">
            <a
              v-for="social in socialLinks"
              :key="social.name"
              :href="social.url"
              target="_blank"
              rel="noopener noreferrer"
              class="social-link"
              :title="social.name"
            >
              <el-icon :size="18">
                <component :is="social.icon" />
              </el-icon>
            </a>
          </div>
        </div>

        <!-- 快速链接 -->
        <div class="footer-section footer-links">
          <h4 class="section-title">快速链接</h4>
          <ul class="link-list">
            <li v-for="link in quickLinks" :key="link.name">
              <router-link :to="link.path" class="footer-link">
                {{ link.name }}
              </router-link>
            </li>
          </ul>
        </div>

        <!-- 产品服务 -->
        <div class="footer-section footer-links">
          <h4 class="section-title">产品服务</h4>
          <ul class="link-list">
            <li v-for="link in productLinks" :key="link.name">
              <router-link :to="link.path" class="footer-link">
                {{ link.name }}
              </router-link>
            </li>
          </ul>
        </div>

        <!-- 联系方式 -->
        <div class="footer-section footer-contact">
          <h4 class="section-title">联系我们</h4>
          <ul class="contact-list">
            <li v-for="contact in contactInfo" :key="contact.type" class="contact-item">
              <el-icon :size="16" class="contact-icon">
                <component :is="contact.icon" />
              </el-icon>
              <span class="contact-text">{{ contact.value }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="footer-divider" />

      <!-- 版权信息 -->
      <div class="footer-bottom">
        <p class="copyright">
          &copy; {{ currentYear }} DocDist. All rights reserved.
        </p>
        <div class="footer-legal">
          <router-link to="/privacy" class="legal-link">隐私政策</router-link>
          <span class="divider">|</span>
          <router-link to="/terms" class="legal-link">服务条款</router-link>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useUiStore } from '@/stores/ui'
import {
  Document,
  Message,
  Phone,
  Location,
  Link
} from '@element-plus/icons-vue'
import { h } from 'vue'

// 社交媒体图标使用 SVG 组件
const Github = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: '20', height: '20' }, [
      h('path', {
        fill: 'currentColor',
        d: 'M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z'
      })
    ])
  }
}

const Twitter = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: '20', height: '20' }, [
      h('path', {
        fill: 'currentColor',
        d: 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z'
      })
    ])
  }
}

// 获取 UI Store
const uiStore = useUiStore()
const isDark = computed(() => uiStore.isDark)

// 当前年份
const currentYear = computed(() => new Date().getFullYear())

// 社交媒体链接
const socialLinks = [
  { name: 'GitHub', url: 'https://github.com', icon: Github },
  { name: 'Twitter', url: 'https://twitter.com', icon: Twitter },
  { name: '官网', url: 'https://docdist.com', icon: Link }
]

// 快速链接
const quickLinks = [
  { name: '首页', path: '/' },
  { name: '项目管理', path: '/admin/projects' },
  { name: '考试安排', path: '/admin/exams' },
  { name: '系统设置', path: '/admin/settings' }
]

// 产品服务链接
const productLinks = [
  { name: '个人中心', path: '/profile' },
  { name: '活动记录', path: '/activities' },
  { name: '管理首页', path: '/admin' },
  { name: '登录入口', path: '/login' }
]

// 联系信息
const contactInfo = [
  { type: 'email', value: 'support@docdist.com', icon: Message },
  { type: 'phone', value: '+86 400-123-4567', icon: Phone },
  { type: 'address', value: '北京市朝阳区科技园区', icon: Location }
]
</script>

<style scoped>
.app-footer {
  background-color: var(--bg-secondary, #ffffff);
  border-top: 1px solid var(--border-color, #e4e7ed);
  padding: 48px 0 24px;
  margin-top: auto;
  transition: background-color var(--transition-normal), border-color var(--transition-normal);
}

.app-footer--dark {
  background-color: var(--bg-secondary, #1d1d1d);
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.footer-content {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  gap: 48px;
  margin-bottom: 32px;
}

.footer-section {
  display: flex;
  flex-direction: column;
}

/* 品牌区域 */
.footer-brand {
  max-width: 320px;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.logo-icon {
  color: var(--color-primary, #1A5276);
}

.brand-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #333333);
}

.brand-desc {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary, #666666);
  margin: 0 0 20px 0;
}

/* 社交媒体链接 */
.social-links {
  display: flex;
  gap: 12px;
}

.social-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: var(--bg-tertiary, #fafafa);
  color: var(--text-secondary, #666666);
  transition: all var(--transition-fast);
}

.social-link:hover {
  background-color: var(--color-primary, #1A5276);
  color: #ffffff;
  transform: translateY(-2px);
}

/* 链接区域 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #333333);
  margin: 0 0 16px 0;
}

.link-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.link-list li {
  margin-bottom: 10px;
}

.footer-link {
  font-size: 14px;
  color: var(--text-secondary, #666666);
  text-decoration: none;
  transition: color var(--transition-fast);
  display: inline-block;
}

.footer-link:hover {
  color: var(--color-primary, #1A5276);
  transform: translateX(4px);
}

/* 联系信息 */
.contact-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary, #666666);
}

.contact-icon {
  color: var(--color-primary, #1A5276);
  flex-shrink: 0;
}

.contact-text {
  word-break: break-all;
}

/* 分隔线 */
.footer-divider {
  height: 1px;
  background-color: var(--border-color, #e4e7ed);
  margin-bottom: 24px;
}

/* 底部版权区 */
.footer-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.copyright {
  font-size: 13px;
  color: var(--text-tertiary, #999999);
  margin: 0;
}

.footer-legal {
  display: flex;
  align-items: center;
  gap: 12px;
}

.legal-link {
  font-size: 13px;
  color: var(--text-secondary, #666666);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.legal-link:hover {
  color: var(--color-primary, #1A5276);
}

.divider {
  color: var(--border-color-dark, #d4d7de);
}

/* 响应式布局 */
@media (max-width: 992px) {
  .footer-content {
    grid-template-columns: 1fr 1fr;
    gap: 32px;
  }

  .footer-brand {
    grid-column: 1 / -1;
    max-width: 100%;
  }
}

@media (max-width: 576px) {
  .app-footer {
    padding: 32px 0 20px;
  }

  .footer-container {
    padding: 0 16px;
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: 24px;
    margin-bottom: 24px;
  }

  .footer-bottom {
    flex-direction: column;
    text-align: center;
  }

  .footer-legal {
    justify-content: center;
  }
}
</style>
