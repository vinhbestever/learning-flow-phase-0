/** Nhóm theo phần đầu tiêu đề (vd. "Unit 2C: Shopping - Lesson 5" → "Unit 2C: Shopping") */
export function moduleLabelFromTitle(title: string): string {
  const i = title.indexOf(' - ')
  if (i === -1) return title.trim() || 'Khác'
  return title.slice(0, i).trim() || 'Khác'
}

export type WithTitlePos = { title: string; position?: number | null }

export function groupLessonsByModule<T extends WithTitlePos>(items: T[]): [string, T[]][] {
  const map = new Map<string, T[]>()
  for (const item of items) {
    const mod = moduleLabelFromTitle(item.title)
    const arr = map.get(mod) ?? []
    arr.push(item)
    map.set(mod, arr)
  }
  const entries = [...map.entries()]
  for (const [, rows] of entries) {
    rows.sort((a, b) => (a.position ?? 9999) - (b.position ?? 9999))
  }
  entries.sort((a, b) => {
    const minPos = (rows: T[]) =>
      rows.length ? Math.min(...rows.map((x) => x.position ?? 9999)) : 9999
    return minPos(a[1]) - minPos(b[1])
  })
  return entries
}

/** Lịch sử: nhóm theo unit; trong nhóm sắp theo gần luyện nhất trước */
export type HistoryRow = { title: string; days_since_last_practice: number | null }

export function groupHistoryByModule<T extends HistoryRow>(items: T[]): [string, T[]][] {
  const map = new Map<string, T[]>()
  for (const item of items) {
    const mod = moduleLabelFromTitle(item.title)
    const arr = map.get(mod) ?? []
    arr.push(item)
    map.set(mod, arr)
  }
  const entries = [...map.entries()]
  for (const [, rows] of entries) {
    rows.sort(
      (a, b) =>
        (a.days_since_last_practice ?? 9999) - (b.days_since_last_practice ?? 9999),
    )
  }
  entries.sort((a, b) => {
    const minDays = (rows: T[]) =>
      rows.length ? Math.min(...rows.map((x) => x.days_since_last_practice ?? 9999)) : 9999
    return minDays(a[1]) - minDays(b[1])
  })
  return entries
}
