/** Folder names like `2111414_newstudent` or `1792706_newstudent_0` under output/. */

const NEWSTUDENT_RE = /^(\d+)_newstudent(?:_(.+))?$/i

export type StudentFolderLabel = {
  /** Full folder name (URL segment). */
  raw: string
  isNewStudent: boolean
  /** Leading digits for display (e.g. `1585392`). */
  displayId: string
  /** Optional suffix after `_newstudent_` (e.g. `0`). */
  variant: string | null
}

export function parseStudentFolderId(studentId: string): StudentFolderLabel {
  const raw = String(studentId).trim()
  const m = raw.match(NEWSTUDENT_RE)
  if (m) {
    return {
      raw,
      isNewStudent: true,
      displayId: m[1],
      variant: m[2] != null && m[2] !== '' ? m[2] : null,
    }
  }
  return { raw, isNewStudent: false, displayId: raw, variant: null }
}
