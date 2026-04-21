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
  easy: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  medium: 'border-amber-200 bg-amber-50 text-amber-950',
  hard: 'border-rose-200 bg-rose-50 text-rose-900',
}

const skillStyle: Record<string, string> = {
  grammar: 'border-sky-200 bg-sky-50 text-sky-900',
  vocabulary: 'border-violet-200 bg-violet-50 text-violet-900',
  speaking: 'border-orange-200 bg-orange-50 text-orange-900',
  pronunciation: 'border-fuchsia-200 bg-fuchsia-50 text-fuchsia-900',
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
      <div className="space-y-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-card)]">
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
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Bài về nhà
          </p>
          <h1 className="font-display mt-1 text-2xl font-semibold text-[var(--ink)] md:text-3xl">
            {data.homework.length} câu đã chọn
          </h1>
          <p className="mt-1 max-w-xl text-xs text-[var(--muted)]">
            Phần <span className="font-semibold text-[var(--mint)]">Lý do giao bài</span> giải thích vì
            sao câu này phù hợp với học sinh — đọc trước khi xem đề.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowDiag((d) => !d)}
          className="shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--mint)]/40 hover:text-[var(--ink)]"
        >
          {showDiag ? 'Ẩn đánh giá' : 'Đánh giá đầy đủ'}
        </button>
      </header>

      {showDiag && (
        <section className="max-h-[min(50vh,420px)] overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
            Diagnostic
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">
            {data.diagnostic}
          </p>
        </section>
      )}

      <ol className="space-y-3">
        {data.homework.map((q, i) => (
          <li
            key={q.question_no}
            className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm"
            style={{ animationDelay: `${Math.min(i, 12) * 0.03}s` }}
          >
            {/* Hàng meta gọn */}
            <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border)] bg-[var(--void)]/40 px-3 py-2">
              <span className="font-display w-7 text-center text-xs font-bold tabular-nums text-[var(--muted)]">
                {q.question_no}
              </span>
              <span
                className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${skillStyle[q.skill_category] ?? skillStyle.other}`}
              >
                {q.skill_category}
              </span>
              <span
                className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${difficultyStyle[q.difficulty]}`}
              >
                {q.difficulty}
              </span>
              <span className="rounded-md border border-[var(--border)] bg-[var(--elevated)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                {q.question_type}
              </span>
              <span className="ml-auto min-w-0 truncate pl-2 text-right text-[10px] text-[var(--muted)]">
                {q.lesson_title}
              </span>
            </div>

            {/* Lý do — trọng tâm UI */}
            <div className="relative border-b border-[var(--mint)]/20 bg-gradient-to-br from-[var(--mint-soft)]/90 via-[#f0fdf9] to-[var(--amber-soft)]/50 px-4 py-4">
              <div
                className="pointer-events-none absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-[var(--mint)] to-[var(--amber)]"
                aria-hidden
              />
              <p className="pl-3 font-display text-[10px] font-semibold uppercase tracking-[0.35em] text-[var(--mint)]">
                Lý do giao bài
              </p>
              <p className="mt-2 pl-3 text-sm font-medium leading-relaxed text-[var(--ink)] md:text-[0.9375rem]">
                {q.reason}
              </p>
            </div>

            {/* Đề + đáp án — nhẹ hơn */}
            <div className="space-y-2 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                Câu hỏi
              </p>
              <p className="text-sm leading-relaxed text-[var(--ink)]">{q.question_text}</p>
              {q.correct_answer && (
                <p className="rounded-lg border border-dashed border-[var(--mint)]/40 bg-[var(--mint-soft)]/30 px-2.5 py-1.5 text-xs">
                  <span className="font-semibold text-[var(--mint)]">Đáp án:</span>{' '}
                  <span className="text-[var(--ink)]">{q.correct_answer}</span>
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
