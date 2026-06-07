/**
 * Playwright E2E 测试配置文件
 * 配置端到端测试的浏览器、并行执行、截图和视频等
 *
 * @see https://playwright.dev/docs/test-configuration
 */
import { defineConfig, devices } from '@playwright/test'

/**
 * 从环境变量读取配置
 */
const PORT = process.env.PORT || 3000
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`

export default defineConfig({
  // ==================== 基础配置 ====================

  // 测试文件匹配模式
  testMatch: '**/*.e2e.spec.{js,ts}',

  // 测试文件目录
  testDir: './e2e',

  // 全局超时时间（毫秒）
  globalTimeout: 10 * 60 * 1000, // 10 分钟

  // 每个测试的超时时间（毫秒）
  timeout: 30 * 1000, // 30 秒

  // 全局前置脚本路径
  globalSetup: './e2e/global-setup.js',

  // 全局后置脚本路径
  globalTeardown: './e2e/global-teardown.js',

  // ==================== 并行执行配置 ====================

  // 并行执行工作进程数
  // 使用 undefined 表示自动根据 CPU 核心数决定
  workers: process.env.CI ? 1 : undefined,

  // 是否完全并行执行（每个文件一个工作进程）
  fullyParallel: true,

  // 失败测试的重试次数
  // CI 环境重试 2 次，本地不重试
  retries: process.env.CI ? 2 : 0,

  // 禁止并行执行的测试模式
  forbidOnly: !!process.env.CI,

  // ==================== 报告器配置 ====================

  reporter: [
    // 列表格式报告器
    ['list'],
    // HTML 报告器
    ['html', { outputFolder: './playwright-report' }],
    // JUnit XML 报告器（用于 CI 集成）
    ['junit', { outputFile: './test-results/junit.xml' }]
  ],

  // ==================== 共享配置 ====================

  use: {
    // 基础 URL
    baseURL: BASE_URL,

    // 追踪配置
    // 可选值: 'on', 'off', 'retain-on-failure', 'on-first-retry'
    trace: 'on-first-retry',

    // 截图配置
    // 可选值: 'on', 'off', 'only-on-failure'
    screenshot: 'only-on-failure',

    // 视频配置
    // 可选值: 'on', 'off', 'retain-on-failure', 'on-first-retry'
    video: 'on-first-retry',

    // 视口大小
    viewport: { width: 1280, height: 720 },

    // 动作超时时间（毫秒）
    actionTimeout: 15000,

    // 导航超时时间（毫秒）
    navigationTimeout: 15000,

    // 是否忽略 HTTPS 错误
    ignoreHTTPSErrors: true,

    // 测试隔离级别
    // 'test' - 每个测试之间清理上下文
    // 'worker' - 每个工作进程清理上下文
    testIdAttribute: 'data-testid'
  },

  // ==================== 项目配置（浏览器） ====================

  projects: [
    // Chromium 浏览器配置
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // 启动参数
        launchOptions: {
          args: ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
        }
      }
    },

    // Firefox 浏览器配置
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        // Firefox 特定配置
        launchOptions: {
          firefoxUserPrefs: {
            // 禁用更新检查
            'app.update.auto': false,
            'app.update.enabled': false
          }
        }
      }
    },

    // WebKit 浏览器配置（Safari）
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari']
      }
    },

    // 移动端 Chromium 配置
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5']
      },
      // 只在特定标签时运行
      grep: /@mobile/
    },

    // 移动端 Safari 配置
    {
      name: 'Mobile Safari',
      use: {
        ...devices['iPhone 12']
      },
      // 只在特定标签时运行
      grep: /@mobile/
    }
  ],

  // ==================== 本地开发服务器配置 ====================

  webServer: {
    // 启动命令
    command: 'npm run dev',

    // 服务器 URL
    url: BASE_URL,

    // 超时时间（毫秒）
    timeout: 120 * 1000, // 2 分钟

    // 是否重用已有服务器
    reuseExistingServer: !process.env.CI,

    // 环境变量
    env: {
      NODE_ENV: 'test'
    },

    // 服务器输出日志
    stdout: 'pipe',
    stderr: 'pipe'
  },

  // ==================== 输出目录配置 ====================

  // 测试结果输出目录
  outputDir: './test-results',

  // 快照测试目录
  snapshotDir: './e2e/snapshots',

  // 快照测试序列化器
  expect: {
    // 快照测试超时时间
    timeout: 5000,

    // 自定义匹配器
    toMatchSnapshot: {
      // 最大差异像素
      maxDiffPixels: 100,
      // 最大差异比例
      maxDiffPixelRatio: 0.1
    }
  }
})
