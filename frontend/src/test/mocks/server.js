/**
 * MSW (Mock Service Worker) 服务器配置
 * 用于测试环境中拦截和处理 HTTP 请求
 */
import { setupServer } from 'msw/node'
import { handlers } from './handlers.js'

/**
 * 创建 MSW 服务器实例
 * 使用 handlers.js 中定义的所有请求处理器
 */
export const server = setupServer(...handlers)

/**
 * 服务器生命周期方法说明：
 *
 * server.listen(options) - 启动服务器并开始拦截请求
 *   options.onUnhandledRequest: 处理未匹配请求的策略
 *     - 'bypass': 让请求通过（默认）
 *     - 'warn': 在控制台输出警告
 *     - 'error': 抛出错误
 *
 * server.resetHandlers(...handlers) - 重置处理器到初始状态
 *   可用于在单个测试中临时覆盖处理器
 *
 * server.close() - 停止服务器并恢复原始 fetch 行为
 *
 * server.use(...handlers) - 临时添加处理器
 *   在 resetHandlers 调用后会被清除
 */
