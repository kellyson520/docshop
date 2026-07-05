import { describe, expect, it } from 'vitest'
import { filterShareFiles } from '../shareProjectSearch'

describe('filterShareFiles', () => {
  const files = [
    { id: '1', original_filename: '线性代数期末复习.pdf', filename: 'linear-final.pdf', display_name: '线代复习', file_type: 'pdf', latest_changelog: '新增答案' },
    { id: '2', original_filename: '大学物理讲义.docx', filename: 'physics.docx', display_name: '物理讲义', file_type: 'docx', latest_changelog: '更新封面' }
  ]

  it('按中文文件名过滤分享项目内文件', () => {
    expect(filterShareFiles(files, '线性代数').map(file => file.id)).toEqual(['1'])
  })

  it('空关键字返回全部文件', () => {
    expect(filterShareFiles(files, '').map(file => file.id)).toEqual(['1', '2'])
  })
})
