import { useEffect, useState } from 'react'

interface StudentSummary {
  student_id: number
  reference_date?: string
  total_lessons: number
  overall_pronunciation_score_avg: number
  overall_free_speaking_score_avg: number
  overall_homework_skill_breakdown: Record<
    string,
    { correct: number; total: number; accuracy: number }
  >
  lessons_by_status: Record<string, number>
  overall_free_speaking_answer_type_dist: Record<string, number>
  weak_skills_global: string[]
}

const LESSON_STATUS_LABEL: Record<string, string> = {
  completed: 'Đã hoàn thành',
  in_class_only: 'Chỉ trong lớp',
  not_started: 'Chưa bắt đầu',
  in_progress: 'Đang học',
}

const SPEAKING_TYPE_LABEL: Record<string, string> = {
  correct: 'Đúng',
  incorrect: 'Sai',
  accordant: 'Khớp',
  inaccordant: 'Không khớp',
  lack_of_knowledge: 'Thiếu kiến thức',
}

const SPEAKING_TYPE_COLOR: Record<string, string> = {
  correct: 'bg-[var(--mint)]',
  incorrect: 'bg-[var(--coral)]',
  accordant: 'bg-sky-500',
  inaccordant: 'bg-[var(--amber)]',
  lack_of_knowledge: 'bg-[var(--muted)]',
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

export default function StudentProfile() {
  const [data, setData] = useState<StudentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/student')
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [])

  const skills = data ? Object.entries(data.overall_homework_skill_breakdown) : []
  const speakingDist = data ? Object.entries(data.overall_free_speaking_answer_type_dist) : []
  const speakingTotal = speakingDist.reduce((s, [, n]) => s + n, 0)
  const completed = data ? (data.lessons_by_status['completed'] ?? 0) : 0
  const completionPct =
    data && data.total_lessons > 0
      ? Math.min(100, Math.round((completed / data.total_lessons) * 100))
      : 0
  const otherStatuses = data
    ? Object.entries(data.lessons_by_status).filter(([k]) => k !== 'completed')
    : []

  if (error) {
    return (
      <div className="animate-rise rounded-2xl border border-[var(--coral)]/35 bg-gradient-to-br from-[#fff1f2] to-[#ffe4e6]/80 p-6 shadow-[var(--shadow-card)]">
        <p className="font-display text-lg font-semibold text-[var(--coral)]">Không tải được hồ sơ</p>
        <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="space-y-8 animate-rise">
        <div className="h-36 animate-pulse rounded-2xl bg-[var(--elevated)]/80" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((k) => (
            <div key={k} className="h-28 animate-pulse rounded-2xl bg-[var(--elevated)]/80" />
          ))}
        </div>
        <div className="h-48 animate-pulse rounded-2xl bg-[var(--elevated)]/80" />
      </div>
    )
  }

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="animate-rise relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-card)]">
        <div
          className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-[var(--mint)]/[0.07]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-[var(--amber)]/[0.06]"
          aria-hidden
        />
        <div className="relative grid gap-8 p-6 md:grid-cols-[1fr_auto] md:items-center md:p-8">
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)]/60 px-2.5 py-0.5 font-display text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
                Tổng quan
              </span>
              {data.reference_date && (
                <span className="text-[11px] tabular-nums text-[var(--muted)]">
                  Cập nhật · {data.reference_date}
                </span>
              )}
            </div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-[var(--ink)] md:text-4xl">
              Học sinh{' '}
              <span className="bg-gradient-to-r from-[var(--mint)] to-[#0f766e] bg-clip-text text-transparent">
                #{data.student_id}
              </span>
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-[var(--muted)]">
              Bức tranh nhanh về Phase 0: tiến độ bài học, điểm phát âm / nói tự do và độ chính xác
              bài tập theo chủ đề.
            </p>
            {data.weak_skills_global.length > 0 && (
              <div className="flex flex-wrap items-start gap-2 rounded-xl border border-[var(--amber)]/35 bg-[var(--amber-soft)]/90 px-3 py-2.5 text-sm text-[var(--ink)]">
                <span className="shrink-0 font-semibold text-[var(--amber)]">Cần luyện thêm:</span>
                <span className="flex flex-wrap gap-1.5">
                  {data.weak_skills_global.map((s) => (
                    <span
                      key={s}
                      className="rounded-md border border-[var(--amber)]/40 bg-white/80 px-2 py-0.5 text-xs font-medium"
                    >
                      {s}
                    </span>
                  ))}
                </span>
              </div>
            )}
          </div>

          <CompletionRing pct={completionPct} completed={completed} total={data.total_lessons} />
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          className="animate-rise delay-1"
          label="Tổng bài học"
          value={data.total_lessons}
          hint="trong lộ trình"
          accent="ink"
        />
        <StatCard
          className="animate-rise delay-2"
          label="Đã hoàn thành"
          value={completed}
          hint={`${completionPct}% lộ trình`}
          accent="mint"
        />
        <StatCard
          className="animate-rise delay-3"
          label="Phát âm TB"
          value={`${data.overall_pronunciation_score_avg.toFixed(1)}`}
          suffix="/100"
          hint="Digital Teacher"
          accent="amber"
        />
        <StatCard
          className="animate-rise delay-4"
          label="Nói tự do TB"
          value={`${data.overall_free_speaking_score_avg.toFixed(1)}`}
          suffix="/100"
          hint="free speaking"
          accent="mint"
        />
      </section>


      <section className="animate-rise delay-5 space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold text-[var(--ink)] md:text-xl">
              Kỹ năng theo chủ đề
            </h2>
            <p className="mt-1 text-xs text-[var(--muted)]">Độ chính xác bài tập (LMS) theo nhóm</p>
          </div>
          <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--muted)]">
            {skills.length} nhóm
          </span>
        </div>

        <div className="space-y-2.5">
          {skills.length === 0 ? (
            <p className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted)]">
              Chưa có dữ liệu skill breakdown.
            </p>
          ) : (
            skills.map(([skill, stats], i) => (
              <div
                key={skill}
                className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm transition hover:border-[var(--mint)]/35 hover:shadow-[var(--shadow-card)]"
                style={{ animationDelay: `${0.04 * i}s` }}
              >
                <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 gap-y-1">
                  <span className="min-w-0 font-medium leading-snug text-[var(--ink)] line-clamp-2">
                    {skill}
                  </span>
                  <span className="shrink-0 tabular-nums text-xs text-[var(--muted)] sm:text-sm">
                    {stats.correct}/{stats.total} ·{' '}
                    <span className="font-semibold text-[var(--mint)]">
                      {(stats.accuracy * 100).toFixed(0)}%
                    </span>
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--elevated-2)]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--mint)] to-[var(--amber)] transition-all duration-700 group-hover:brightness-[1.05]"
                    style={{ width: `${Math.min(100, stats.accuracy * 100)}%` }}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function CompletionRing({
  pct,
  completed,
  total,
}: {
  pct: number
  completed: number
  total: number
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 md:min-w-[9.5rem]">
      <div
        className="relative grid h-28 w-28 place-items-center rounded-full p-[3px] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]"
        style={{
          background: `conic-gradient(var(--mint) ${pct * 3.6}deg, var(--elevated-2) 0deg)`,
        }}
      >
        <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-[var(--surface)] text-center">
          <span className="font-display text-2xl font-bold tabular-nums text-[var(--ink)]">{pct}%</span>
          <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
            hoàn thành
          </span>
        </div>
      </div>
      <p className="text-center text-[11px] tabular-nums text-[var(--muted)]">
        {completed}/{total} bài
      </p>
    </div>
  )
}

function StatCard({
  label,
  value,
  suffix,
  hint,
  className = '',
  accent = 'ink',
}: {
  label: string
  value: string | number
  suffix?: string
  hint?: string
  className?: string
  accent?: 'mint' | 'amber' | 'ink'
}) {
  const edge =
    accent === 'mint'
      ? 'border-l-[var(--mint)]'
      : accent === 'amber'
        ? 'border-l-[var(--amber)]'
        : 'border-l-[var(--ink)]/25'

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-[var(--border)] border-l-4 ${edge} bg-[var(--surface)] p-4 shadow-[var(--shadow-card)] ${className}`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
        {label}
      </p>
      <p className="font-display mt-2 text-2xl font-semibold tabular-nums text-[var(--ink)] md:text-3xl">
        {value}
        {suffix && <span className="text-base font-medium text-[var(--muted)] md:text-lg">{suffix}</span>}
      </p>
      {hint && <p className="mt-1.5 text-[11px] text-[var(--muted)]">{hint}</p>}
    </div>
  )
}
