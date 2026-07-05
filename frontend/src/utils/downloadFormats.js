function normalizeDownloadFormat(format) {
  return String(format || '').trim().toLowerCase()
}

function normalizeFormatList(formats) {
  if (!Array.isArray(formats)) return []
  return formats
    .map(normalizeDownloadFormat)
    .filter(Boolean)
}

export function inferOriginalDownloadFormat(file = null, version = null) {
  const explicitOriginal = normalizeDownloadFormat(
    version?.original_download_format
    || file?.original_download_format
    || file?.originalFormat,
  )

  if (explicitOriginal) {
    return explicitOriginal
  }

  return normalizeDownloadFormat(file?.file_type || file?.filename?.split('.').pop())
}

export function resolveDownloadFormats(file = null, version = null) {
  const merged = []
  const appendFormats = (formats) => {
    for (const format of normalizeFormatList(formats)) {
      if (!merged.includes(format)) {
        merged.push(format)
      }
    }
  }

  appendFormats(version?.download_formats)
  appendFormats(file?.download_formats)

  const originalFormat = inferOriginalDownloadFormat(file, version)
  if (merged.length === 0) {
    return originalFormat ? [originalFormat] : []
  }

  if (originalFormat && merged.includes(originalFormat)) {
    return [originalFormat, ...merged.filter((format) => format !== originalFormat)]
  }

  return merged
}

export function hasSingleDownloadFormat(file = null, version = null) {
  return resolveDownloadFormats(file, version).length === 1
}

export function hasMultipleDownloadFormats(file = null, version = null) {
  if (version?.has_alternate_downloads === true || file?.has_alternate_downloads === true) {
    return true
  }

  return resolveDownloadFormats(file, version).length > 1
}

export function isOriginalDownloadFormat(file = null, format = '', version = null) {
  const normalizedFormat = normalizeDownloadFormat(format)
  const originalFormat = inferOriginalDownloadFormat(file, version)
  if (originalFormat) {
    return normalizedFormat === originalFormat
  }

  const formats = resolveDownloadFormats(file, version)
  return formats.length > 0 ? normalizedFormat === formats[0] : false
}

export function getDownloadFormatLabel(format) {
  const normalized = normalizeDownloadFormat(format)
  const map = {
    doc: 'Word 下载',
    docx: 'Word 下载',
    pdf: 'PDF 下载',
    xls: 'Excel 下载',
    xlsx: 'Excel 下载',
    ppt: 'PPT 下载',
    pptx: 'PPT 下载',
    mp4: 'MP4 下载',
    html: 'HTML 下载',
    zip: 'ZIP 下载',
    '7z': '7Z 下载',
  }
  return map[normalized] || `${normalized.toUpperCase()} 下载`
}
