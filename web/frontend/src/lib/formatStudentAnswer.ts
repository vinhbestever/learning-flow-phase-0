/**
 * Human-readable display for LMS `bai_lam` / `student_answer` payloads
 * (strings, arrays of primitives, or arrays of { u, is_correct }).
 */
export function formatStudentAnswerDisplay(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)

  if (Array.isArray(value)) {
    if (value.length === 0) return ''

    const allScalar = value.every(
      (x) => x == null || typeof x === 'string' || typeof x === 'number' || typeof x === 'boolean',
    )
    if (allScalar) {
      return value.map((x) => String(x)).join(' · ')
    }

    return value
      .map((item) => {
        if (item != null && typeof item === 'object' && 'u' in item) {
          const u = (item as { u?: unknown }).u
          const ok = (item as { is_correct?: number }).is_correct
          const mark = ok === 1 ? '✓' : ok === 0 ? '✗' : ''
          const base = u == null ? '' : String(u)
          return mark ? `${base} ${mark}` : base
        }
        try {
          return JSON.stringify(item)
        } catch {
          return String(item)
        }
      })
      .filter(Boolean)
      .join(' | ')
  }

  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }

  return String(value)
}
