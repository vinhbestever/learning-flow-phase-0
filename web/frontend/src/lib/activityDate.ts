/** Parse LMS-style `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS` as local wall time (avoids UTC date-only shifts). */
export function parseActivityDateLocal(raw: string | null): Date | null {
  if (!raw?.trim()) return null
  const t = raw.trim()
  const m = t.match(/^(\d{4})-(\d{2})-(\d{2})(?: (\d{2}):(\d{2}):(\d{2}))?$/)
  if (m) {
    return new Date(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      m[4] != null ? Number(m[4]) : 0,
      m[5] != null ? Number(m[5]) : 0,
      m[6] != null ? Number(m[6]) : 0,
    )
  }
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatActivityDateDisplay(raw: string | null): {
  label: string
  dateTime: string
  title: string
} | null {
  const d = parseActivityDateLocal(raw)
  if (!d || !raw?.trim()) return null
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  const label = new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(d)
  return { label, dateTime: `${y}-${mo}-${da}`, title: raw.trim() }
}
