/**
 * 格式化日期显示
 * @param {string} isoString - ISO 格式日期字符串
 * @returns {string} 格式化后的日期
 */
export function formatDate(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const k = 1024
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1)
  const size = (bytes / Math.pow(k, i)).toFixed(i > 0 ? 2 : 0)
  return `${size} ${units[i]}`
}

/**
 * 获取文件类型图标名
 * @param {string} fileType - 文件类型 (pdf, docx, xlsx 等)
 * @returns {string} Element Plus 图标名
 */
export function getFileTypeIcon(fileType) {
  const iconMap = {
    pdf: 'Document',
    docx: 'Document',
    doc: 'Document',
    xlsx: 'Grid',
    xls: 'Grid',
    csv: 'Grid',
    txt: 'Document',
    default: 'Document'
  }
  return iconMap[fileType] || iconMap.default
}

/**
 * 下载 Blob 并处理 HTML fallback（用于 PDF 转换）
 *
 * 服务端在 LibreOffice 不可用时返回 HTML（text/html）而非 PDF。
 * 此函数检测响应类型：
 * - application/pdf / blob → 直接触发浏览器下载
 * - text/html → 在新窗口中打开并触发打印（用户可保存为 PDF）
 *
 * @param {Blob} blob - 服务端返回的 Blob
 * @param {string} filename - 下载文件名
 */
export function downloadBlobWithFallback(blob, filename) {
  const contentType = (blob.type || '').toLowerCase()

  if (contentType.includes('text/html') || contentType.includes('html')) {
    // HTML fallback??? blob URL ????????? HTML ??????????
    const url = window.URL.createObjectURL(blob)
    const win = window.open(url, '_blank', 'width=900,height=700')
    if (win) {
      setTimeout(() => {
        try { win.print() } catch {}
      }, 800)
    }
    setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 10000)
  } else {
    // 正常 Blob 下载（PDF / Word）
    triggerDownload(blob, filename)
  }
}

/**
 * 触发浏览器下载 Blob。
 * 将 <a> 添加到 DOM 后再点击（部分浏览器要求），
 * 延迟 revokeObjectURL 防止下载被中断。
 */
function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  // 延迟清理：确保浏览器已开始读取 blob 后再释放
  setTimeout(() => {
    try {
      if (a.parentNode) {
        document.body.removeChild(a)
      }
    } finally {
      window.URL.revokeObjectURL(url)
    }
  }, 1000)
}

/**
 * 通过直接 URL 导航触发下载（绕过广告拦截器）。
 *
 * 部分广告拦截器会拦截 XHR/fetch 请求中 URL 包含 "download" 的路径。
 * 此函数使用隐藏 iframe 直接加载下载链接，不会被拦截。
 *
 * @param {string} apiUrl - API 下载地址（如 /api/v1/share/.../download/pdf）
 * @param {string} filename - 建议的文件名（备用）
 */
export function downloadViaIframe(apiUrl) {
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = apiUrl
  document.body.appendChild(iframe)
  // 10 秒后清理 iframe
  setTimeout(() => {
    if (iframe.parentNode) {
      document.body.removeChild(iframe)
    }
  }, 10000)
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否复制成功
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }
}
