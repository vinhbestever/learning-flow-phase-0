import { useEffect, useState } from 'react'

interface Lesson {
  lesson_id: number
  title: string
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
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/lessons')
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setLessons)
      .catch((e: unknown) => setError(String(e)))
  }, [])

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
    <div className="space-y-10">
      <header className="animate-rise flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Khóa học
          </p>
          <h1 className="font-display mt-2 text-3xl font-semibold text-[var(--ink)] md:text-4xl">
            Danh sách bài học
          </h1>
        </div>
        <div className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--muted)]">
          <span className="font-semibold text-[var(--ink)]">{lessons.length}</span> bài trong export
        </div>
      </header>

      <ol className="space-y-4">
        {lessons.map((l, i) => (
          <li
            key={l.lesson_id}
            className="animate-rise group relative overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-card)] transition hover:border-[var(--amber)]/35"
            style={{ animationDelay: `${Math.min(i, 12) * 0.03}s` }}
          >
            <div className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-[var(--amber-soft)]/80 blur-3xl transition group-hover:bg-[var(--amber)]/15" />
            <div className="relative flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex gap-4">
                <span className="font-display mt-1 text-sm tabular-nums text-[var(--muted)]">
                  {String(l.position ?? i + 1).padStart(2, '0')}
                </span>
                <div>
                  <p className="font-display text-lg font-semibold text-[var(--ink)]">{l.title}</p>
                  {l.desc ? (
                    <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-[var(--muted)]">
                      {l.desc}
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 md:flex-col md:items-end">
                {l.level != null && (
                  <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)] px-3 py-1 text-xs font-semibold text-[var(--mint)]">
                    Cấp {l.level}
                  </span>
                )}
                {l.last_activity_date && (
                  <span className="text-xs tabular-nums text-[var(--muted)]">
                    {l.last_activity_date}
                  </span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
