export function resolveCoverUrl(coverImage) {
  if (!coverImage) return ''

  const cover = String(coverImage).replace(/\\/g, '/').trim()
  if (!cover) return ''
  if (/^https?:\/\//i.test(cover) || cover.startsWith('data:') || cover.startsWith('blob:')) {
    return cover
  }
  if (cover.startsWith('/api/v1/covers/')) return cover
  if (cover.startsWith('api/v1/covers/')) return `/${cover}`
  if (cover.startsWith('/covers/')) return `/api/v1${cover}`
  if (cover.startsWith('covers/')) return `/api/v1/${cover}`
  if (cover.startsWith('/api/')) return cover

  return cover.startsWith('/') ? cover : `/api/v1/${cover}`
}
