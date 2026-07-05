const OFFICE_EXTENSIONS = new Set(['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'])
const COMPOUND_EXTENSIONS = ['tar.gz', 'tar.bz2', 'tar.xz']
const ARCHIVE_EXTENSIONS = new Set(['zip', 'rar', '7z', 'tar', 'gz', 'tgz', 'tbz2', 'txz', ...COMPOUND_EXTENSIONS])
const VIDEO_EXTENSIONS = new Set(['mp4', 'webm', 'mov'])
const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'])
const HTML_EXTENSIONS = new Set(['html'])

export function getFileExtension(input = '') {
  if (typeof input !== 'string') return ''
  const normalized = input.trim().toLowerCase()
  const compound = COMPOUND_EXTENSIONS.find((ext) => normalized.endsWith(`.${ext}`))
  if (compound) {
    return compound
  }
  return normalized.split('.').pop() || ''
}

export function deriveClientProfile(filename = '') {
  const ext = getFileExtension(filename)

  if (ARCHIVE_EXTENSIONS.has(ext)) {
    return {
      ext,
      category: 'archive',
      preview_mode: 'structure',
      can_preview: true,
      can_play: false,
      can_diff_visual: false,
      can_diff_structural: true,
      can_generate_thumbnail: false,
    }
  }

  if (VIDEO_EXTENSIONS.has(ext)) {
    return {
      ext,
      category: 'video',
      preview_mode: 'native',
      can_preview: true,
      can_play: true,
      can_diff_visual: true,
      can_diff_structural: false,
      can_generate_thumbnail: true,
    }
  }

  if (IMAGE_EXTENSIONS.has(ext)) {
    return {
      ext,
      category: 'image',
      preview_mode: 'native',
      can_preview: true,
      can_play: false,
      can_diff_visual: true,
      can_diff_structural: false,
      can_generate_thumbnail: true,
    }
  }

  if (ext === 'pdf') {
    return {
      ext,
      category: 'pdf',
      preview_mode: 'native',
      can_preview: true,
      can_play: false,
      can_diff_visual: true,
      can_diff_structural: false,
      can_generate_thumbnail: true,
    }
  }

  if (HTML_EXTENSIONS.has(ext)) {
    return {
      ext,
      category: 'html',
      preview_mode: 'native',
      can_preview: true,
      can_play: false,
      can_diff_visual: false,
      can_diff_structural: false,
      can_generate_thumbnail: false,
    }
  }

  if (OFFICE_EXTENSIONS.has(ext)) {
    return {
      ext,
      category: 'office',
      preview_mode: 'converted',
      can_preview: true,
      can_play: false,
      can_diff_visual: true,
      can_diff_structural: false,
      can_generate_thumbnail: true,
    }
  }

  return {
    ext,
    category: 'binary',
    preview_mode: 'fallback',
    can_preview: false,
    can_play: false,
    can_diff_visual: false,
    can_diff_structural: false,
    can_generate_thumbnail: false,
  }
}

export function buildClientPreviewManifest(file = {}, analysisSummary = {}) {
  const filename = file?.filename || file?.original_filename || file?.display_name || file?.file_type || ''
  const profile = deriveClientProfile(filename.includes('.') ? filename : `file.${filename}`)

  if (profile.category === 'video') {
    return { type: 'video_native', status: 'ready', summary: analysisSummary }
  }
  if (profile.category === 'image') {
    return { type: 'image_native', status: 'ready', summary: analysisSummary }
  }
  if (profile.category === 'pdf') {
    return { type: 'pdf_native', status: 'ready', summary: analysisSummary }
  }
  if (profile.category === 'html') {
    return { type: 'html_runtime', status: 'ready', summary: analysisSummary }
  }
  if (profile.category === 'office') {
    return { type: 'office_pdf', status: 'ready', summary: analysisSummary }
  }
  if (profile.category === 'archive') {
    return { type: 'archive_structure', status: 'ready', summary: analysisSummary }
  }

  return { type: 'fallback', status: 'not_supported', summary: analysisSummary }
}
