import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CollapsibleModule } from '../components/CollapsibleModule'
import { groupLessonsByModule } from '../lib/lessonGroups'

interface Lesson {
  lesson_id: number
  title: string | null
  level: number | null
  position: number | null
  last_activity_date: string | null
  desc: string
}

async function errorMessage(r: Response): Promise<string> {
  try {
    const e = await r.json()
    if (typeof e.detail === 'string') return e.detail
    if (Array.isArray(e.detail))
      return e.detail.map((x: { msg?: string }) => x.msg ?? '').filter(Boolean).join(', ')
  } catch {
    /* ignore */
  }
  return r.statusText || 'Lỗi không xác định'
}

export default function LessonList() {
  const { studentId } = useParams<{ studentId: string }>()
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!studentId) return
    setLessons(null)
    setError(null)
    fetch(`/api/students/${studentId}/lessons`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setLessons)
      .catch((e: unknown) => setError(String(e)))
  }, [studentId])

  const grouped = useMemo(() => (lessons ? groupLessonsByModule(lessons) : []), [lessons])

  if (!studentId) {
    return <p className="text-[var(--muted)]">Thiếu mã học sinh trong URL.</p>
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-[var(--coral)]/30 bg-[#fff1f2] p-6 text-[var(--coral)] shadow-[var(--shadow-card)]">
        <p className="font-display text-lg font-semibold">Không tải được danh sách</p>
        <p className="mt-2 text-sm text-[var(--muted)]">{error}</p>
      </div>
    )
  }

  if (lessons === null) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--amber)]" />
        Đang tải bài học…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="animate-rise flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Khóa học
          </p>
          <h1 className="font-display mt-1 text-2xl font-semibold text-[var(--ink)] md:text-3xl">
            Danh sách bài học
          </h1>
        </div>
        <div className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--muted)]">
          <span className="font-semibold text-[var(--ink)]">{lessons.length}</span> bài ·{' '}
          <span className="font-semibold text-[var(--ink)]">{grouped.length}</span> nhóm
        </div>
      </header>

      <div className="space-y-3">
        {grouped.map(([moduleLabel, rows], gi) => (
          <CollapsibleModule
            key={moduleLabel}
            label={moduleLabel}
            count={rows.length}
            defaultOpen={gi === 0}
          >
            <ul className="grid gap-1 xl:grid-cols-2">
              {rows.map((l, i) => (
                <li key={l.lesson_id}>
                  <Link
                    to={`${l.lesson_id}`}
                    title={l.desc ? l.desc.slice(0, 280) : undefined}
                    className="flex min-h-[3rem] items-center gap-2 rounded-xl border border-transparent px-2 py-2 text-sm outline-none transition hover:border-[var(--mint)]/35 hover:bg-[var(--surface)] focus-visible:ring-2 focus-visible:ring-[var(--mint)]"
                  >
                    <span className="w-7 shrink-0 text-center font-display text-xs tabular-nums text-[var(--muted)]">
                      {String(l.position ?? i + 1).padStart(2, '0')}
                    </span>
                    <span className="min-w-0 flex-1 leading-snug">
                      <span className="font-medium text-[var(--ink)] line-clamp-2 md:line-clamp-1">
                        {l.title?.trim() || `Bài học #${l.lesson_id}`}
                      </span>
                    </span>
                    <span className="hidden shrink-0 text-xs tabular-nums text-[var(--muted)] sm:inline">
                      {l.last_activity_date ?? '—'}
                    </span>
                    {l.level != null && (
                      <span className="shrink-0 rounded-md border border-[var(--mint)]/30 bg-[var(--mint-soft)] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--mint)]">
                        L{l.level}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </CollapsibleModule>
        ))}
      </div>
    </div>
  )
}
