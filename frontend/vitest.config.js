/**
 * Vitest 配置文件
 * 配置单元测试环境、覆盖率、路径别名等
 */
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  // 使用 Vue 插件
  plugins: [vue()],

  // Vitest 测试配置
  test: {
    // 使用 jsdom 作为 DOM 环境
    environment: 'jsdom',

    // 启用全局 API（describe, it, expect 等无需导入）
    globals: true,

    // 测试前置文件路径
    setupFiles: ['./src/test/setup.js'],

    // 覆盖率配置
    coverage: {
      // 使用 v8 作为覆盖率提供者
      provider: 'v8',

      // 覆盖率报告输出目录
      reportsDirectory: '../artifacts/coverage/frontend',

      // 覆盖率报告格式
      reporter: ['text', 'html', 'lcov'],

      // 需要收集覆盖率的文件
      include: ['src/**/*.{js,vue}'],

      // 排除的文件
      exclude: [
        'src/test/**',
        'src/**/*.spec.js',
        'src/**/*.test.js',
        'src/main.js',
        'src/router/index.js'
      ],

      // 覆盖率阈值
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },

    // 测试超时时间（毫秒）
    testTimeout: 10000,

    // 钩子超时时间（毫秒）
    hookTimeout: 10000,

    // 模拟配置
    mockReset: true,

    // 包含的测试文件
    include: ['src/**/*.{test,spec}.{js,mjs,cjs}'],

    // 排除的文件
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache']
  },

  // 路径别名配置
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
