function normalize(value) {
  return String(value || '').trim().toLowerCase()
}

function fileSearchText(file) {
  return [
    file.original_filename,
    file.filename,
    file.display_name,
    file.file_type,
    file.latest_changelog,
    file.id
  ].map(normalize).join(' ')
}

export function filterShareFiles(files, keyword) {
  const query = normalize(keyword)
  if (!query) return files || []
  return (files || []).filter(file => fileSearchText(file).includes(query))
}
