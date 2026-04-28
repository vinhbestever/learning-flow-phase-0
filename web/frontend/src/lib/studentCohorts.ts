import { parseStudentFolderId } from './studentFolderLabel'

/** Học sinh thuộc nhóm trạm (Station) — cập nhật khi thêm folder output mới. */
const STATION_STUDENT_IDS = new Set<string>(['2120773', '2115800', '2116581', '2112511'])

export function isStationStudent(studentId: string | number | null | undefined): boolean {
  if (studentId == null) return false
  const { displayId } = parseStudentFolderId(String(studentId).trim())
  return STATION_STUDENT_IDS.has(displayId)
}
