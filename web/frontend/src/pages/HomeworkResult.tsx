import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface Question {
  question_no: number
  lesson_title: string
  skill_category: string
  question_type: string
  question_text: string
  correct_answer: string | null
  difficulty: 'easy' | 'medium' | 'hard'
  reason: string
}

interface HomeworkData {
  homework: Question[]
  diagnostic: string
}

const difficultyStyle: Record<Question['difficulty'], string> = {
  easy: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  medium: 'border-amber-500/40 bg-amber-500/10 text-amber-100',
  hard: 'border-rose-500/40 bg-rose-500/10 text-rose-100',
}

const skillStyle: Record<string, string> = {
  grammar: 'border-sky-500/35 bg-sky-500/10 text-sky-100',
  vocabulary: 'border-violet-500/35 bg-violet-500/10 text-violet-100',
  speaking: 'border-orange-500/35 bg-orange-500/10 text-orange-100',
  pronunciation: 'border-fuchsia-500/35 bg-fuchsia-500/10 text-fuchsia-100',
  other: 'border-[var(--border)] bg-[var(--elevated)] text-[var(--muted)]',
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

export default function HomeworkResult() {
  const [data, setData] = useState<HomeworkData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDiag, setShowDiag] = useState(false)

  useEffect(() => {
    fetch('/api/homework')
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [])

  if (error) {
    return (
      <div className="space-y-4 rounded-3xl border border-[var(--border)] bg-[var(--surface)]/90 p-8">
        <p className="text-[var(--coral)]">{error}</p>
        <Link
          to="/generate"
          className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--mint)] underline-offset-4 hover:underline"
        >
          Chạy pipeline tạo bài tập
        </Link>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--mint)]" />
        Đang tải bài tập…
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <header className="animate-rise flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Bài về nhà
          </p>
          <h1 className="font-display mt-2 text-3xl font-semibold text-[var(--ink)] md:text-4xl">
            {data.homework.length} câu đã chọn
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setShowDiag((d) => !d)}
          className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-4 py-2 text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--mint)]/40 hover:text-[var(--ink)]"
        >
          {showDiag ? 'Ẩn đánh giá' : 'Xem đánh giá đầy đủ'}
        </button>
      </header>

      {showDiag && (
        <section className="animate-rise rounded-3xl border border-[var(--border)] bg-[var(--surface)]/95 p-6 shadow-[0_32px_100px_-60px_rgba(0,0,0,0.65)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
            Đánh giá học sinh
          </p>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]/95">
            {data.diagnostic}
          </p>
        </section>
      )}

      <ol className="space-y-4">
        {data.homework.map((q, i) => (
          <li
            key={q.question_no}
            className="animate-rise rounded-3xl border border-[var(--border)] bg-[var(--surface)]/90 p-6 shadow-[0_26px_90px_-58px_rgba(232,168,56,0.22)]"
            style={{ animationDelay: `${Math.min(i, 14) * 0.035}s` }}
          >
            <div className="flex gap-4">
              <span className="font-display mt-0.5 w-8 shrink-0 text-sm tabular-nums text-[var(--muted)]">
                {q.question_no}.
              </span>
              <div className="min-w-0 flex-1 space-y-3">
                <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wide">
                  <span
                    className={`rounded-full border px-2.5 py-1 ${skillStyle[q.skill_category] ?? skillStyle.other}`}
                  >
                    {q.skill_category}
                  </span>
                  <span
                    className={`rounded-full border px-2.5 py-1 ${difficultyStyle[q.difficulty]}`}
                  >
                    {q.difficulty}
                  </span>
                  <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-2.5 py-1 text-[var(--muted)]">
                    {q.question_type}
                  </span>
                </div>
                <p className="text-xs text-[var(--muted)]">{q.lesson_title}</p>
                <p className="text-[var(--ink)] leading-relaxed">{q.question_text}</p>
                {q.correct_answer && (
                  <p className="text-sm text-[var(--mint)]">
                    Đáp án: <span className="font-medium">{q.correct_answer}</span>
                  </p>
                )}
                <p className="border-l-2 border-[var(--amber)]/50 pl-3 text-sm italic text-[var(--muted)]">
                  {q.reason}
                </p>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
