import { resolveCoverUrl } from './cover'

export function projectCoverKey(project) {
  return project?.matched_file?.id || project?.first_file?.id || project?.id || ''
}

export function projectCoverUrl(project, failedCoverKeys = new Set()) {
  const key = projectCoverKey(project)
  if (key && failedCoverKeys.has(key)) return ''
  return resolveCoverUrl(project?.cover_image)
}
