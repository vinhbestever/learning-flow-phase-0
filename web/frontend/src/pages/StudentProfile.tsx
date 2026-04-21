import { useEffect, useState } from 'react'

interface StudentSummary {
  student_id: number
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

  if (error) {
    return (
      <div className="animate-rise rounded-3xl border border-[var(--coral)]/35 bg-[var(--elevated)]/80 p-6 text-[var(--coral)] shadow-[0_24px_80px_-40px_rgba(255,123,106,0.45)]">
        <p className="font-display text-lg font-semibold">Không tải được hồ sơ</p>
        <p className="mt-2 text-sm text-[var(--muted)]">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span
          className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--mint)]"
          aria-hidden
        />
        Đang tải dữ liệu học sinh…
      </div>
    )
  }

  const skills = Object.entries(data.overall_homework_skill_breakdown)
  const speakingDist = Object.entries(data.overall_free_speaking_answer_type_dist)

  return (
    <div className="space-y-12">
      <header className="animate-rise space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
          Tổng quan
        </p>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-[var(--ink)] md:text-4xl">
          Học sinh{' '}
          <span className="bg-gradient-to-r from-[var(--mint)] to-[var(--amber)] bg-clip-text text-transparent">
            #{data.student_id}
          </span>
        </h1>
        <p className="max-w-2xl text-[var(--muted)]">
          Ảnh chụp nhanh tiến độ Phase 0: phát âm, nói tự do và độ chính xác bài tập theo chủ đề.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          className="animate-rise delay-1"
          label="Tổng bài học"
          value={data.total_lessons}
          hint="trong lộ trình"
        />
        <StatCard
          className="animate-rise delay-2"
          label="Đã hoàn thành"
          value={data.lessons_by_status['completed'] ?? 0}
          hint="bài đã chốt"
        />
        <StatCard
          className="animate-rise delay-3"
          label="Phát âm TB"
          value={`${data.overall_pronunciation_score_avg.toFixed(1)}`}
          suffix="/100"
          hint="Digital Teacher"
        />
        <StatCard
          className="animate-rise delay-4"
          label="Nói tự do TB"
          value={`${data.overall_free_speaking_score_avg.toFixed(1)}`}
          suffix="/100"
          hint="free speaking"
        />
      </section>

      <section className="animate-rise delay-5 space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="font-display text-xl font-semibold text-[var(--ink)]">
            Kỹ năng theo chủ đề
          </h2>
          <span className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">
            {skills.length} nhóm đang theo dõi
          </span>
        </div>

        <div className="space-y-3">
          {skills.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Chưa có dữ liệu skill breakdown.</p>
          ) : (
            skills.map(([skill, stats], i) => (
              <div
                key={skill}
                className="group rounded-2xl border border-[var(--border)] bg-[var(--surface)]/90 p-5 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)] transition hover:border-[var(--mint)]/35"
                style={{ animationDelay: `${0.05 * i}s` }}
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium text-[var(--ink)]">{skill}</span>
                  <span className="tabular-nums text-[var(--muted)]">
                    {stats.correct}/{stats.total} ·{' '}
                    <span className="text-[var(--mint)]">{(stats.accuracy * 100).toFixed(0)}%</span>
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--elevated-2)]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--mint)] to-[var(--amber)] transition-all duration-700 group-hover:brightness-110"
                    style={{ width: `${Math.min(100, stats.accuracy * 100)}%` }}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="space-y-5">
        <h2 className="font-display text-xl font-semibold text-[var(--ink)]">
          Phân bố câu trả lời nói tự do
        </h2>
        <div className="flex flex-wrap gap-2">
          {speakingDist.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Chưa có phân bố.</p>
          ) : (
            speakingDist.map(([type, count]) => (
              <span
                key={type}
                className="rounded-2xl border border-[var(--border)] bg-[var(--elevated)] px-4 py-2 text-sm text-[var(--muted)] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
              >
                <span className="text-[var(--ink)]">{type}</span>
                <span className="ml-2 font-semibold tabular-nums text-[var(--amber)]">{count}</span>
              </span>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function StatCard({
  label,
  value,
  suffix,
  hint,
  className = '',
}: {
  label: string
  value: string | number
  suffix?: string
  hint?: string
  className?: string
}) {
  return (
    <div
      className={`rounded-3xl border border-[var(--border)] bg-[var(--surface)]/95 p-5 shadow-[0_30px_90px_-55px_rgba(62,207,173,0.35)] ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        {label}
      </p>
      <p className="font-display mt-3 text-3xl font-semibold tabular-nums text-[var(--ink)]">
        {value}
        {suffix && <span className="text-lg text-[var(--muted)]">{suffix}</span>}
      </p>
      {hint && <p className="mt-2 text-xs text-[var(--muted)]">{hint}</p>}
    </div>
  )
}
