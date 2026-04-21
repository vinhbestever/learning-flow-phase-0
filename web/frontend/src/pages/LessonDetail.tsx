import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

interface QuestionRow {
  question_id: number | null
  question_folder: string | null
  question_type: string | null
  question_text: string | null
  requires_media: boolean
  correct_answer: string | null
}

interface PracticeBlock {
  practice_id: number | null
  score: number | null
  correct: number | null
  total: number | null
  submitted_date: string | null
  questions: QuestionRow[]
}

interface LessonDetailData {
  lesson_id: number
  title: string | null
  level: number | null
  position: number | null
  desc: string
  last_activity_date: string | null
  program_id: number | null
  homework: {
    bai_tap: PracticeBlock | null
    luyen_tap: PracticeBlock | null
  }
  in_class_summary: {
    pronunciation_drills: number
    free_speaking: number
    interactive: number
  }
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

function PracticeBlockPanel({
  label,
  block,
}: {
  label: string
  block: PracticeBlock | null
}) {
  if (!block || !block.questions?.length) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--elevated)]/40 px-4 py-3 text-sm text-[var(--muted)]">
        <span className="font-medium text-[var(--ink)]">{label}:</span> chưa có câu hỏi trong export.
      </div>
    )
  }

  const pct =
    block.total != null && block.total > 0 && block.correct != null
      ? Math.round((block.correct / block.total) * 100)
      : null
  const n = block.questions.length

  return (
    <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm transition hover:bg-[var(--void)]/30">
        <span className="font-display font-semibold text-[var(--ink)]">{label}</span>
        <span className="rounded-md bg-[var(--elevated)] px-2 py-0.5 text-xs tabular-nums text-[var(--muted)]">
          {n} câu
        </span>
        {block.score != null && (
          <span className="text-xs font-semibold text-[var(--mint)]">
            {(block.score * 100).toFixed(0)}%
            {pct != null && (
              <span className="ml-1 font-normal text-[var(--muted)]">
                ({block.correct}/{block.total})
              </span>
            )}
          </span>
        )}
        {block.submitted_date && (
          <span className="text-xs tabular-nums text-[var(--muted)]">Nộp {block.submitted_date}</span>
        )}
        <span className="ml-auto text-xs text-[var(--mint)]">Mở / đóng danh sách ▾</span>
      </summary>

      <div className="max-h-[min(65vh,520px)] overflow-y-auto overscroll-contain border-t border-[var(--border)]">
        <ul className="divide-y divide-[var(--border)]">
          {block.questions.map((q, i) => (
            <li key={q.question_id ?? i}>
              <details className="group/q open:bg-[var(--void)]/20 [&>summary::-webkit-details-marker]:hidden">
                <summary className="flex cursor-pointer list-none items-start gap-2 px-3 py-2.5 text-left text-xs">
                  <span className="mt-0.5 w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
                  <span className="min-w-0 flex-1">
                    {q.question_type && (
                      <span className="mr-1 inline-block rounded border border-sky-200 bg-sky-50 px-1 py-0.5 text-[10px] font-medium text-sky-900">
                        {q.question_type}
                      </span>
                    )}
                    {q.requires_media && (
                      <span className="mr-1 inline-block rounded border border-violet-200 bg-violet-50 px-1 py-0.5 text-[10px] text-violet-900">
                        media
                      </span>
                    )}
                    <span className="line-clamp-2 text-[var(--ink)]">{q.question_text}</span>
                  </span>
                  <span className="shrink-0 text-[10px] text-[var(--muted)]">▼</span>
                </summary>
                <div className="space-y-2 border-t border-[var(--border)] bg-[var(--void)]/40 px-3 py-3 pl-11 text-xs leading-relaxed">
                  <p className="text-[var(--ink)]">{q.question_text}</p>
                  {q.correct_answer && (
                    <p className="text-[var(--muted)]">
                      <span className="font-semibold text-[var(--ink)]">Gợi ý:</span>{' '}
                      <span className="break-words">{q.correct_answer}</span>
                    </p>
                  )}
                </div>
              </details>
            </li>
          ))}
        </ul>
      </div>
    </details>
  )
}

export default function LessonDetail() {
  const { lessonId } = useParams<{ lessonId: string }>()
  const id = lessonId ? parseInt(lessonId, 10) : NaN
  const [data, setData] = useState<LessonDetailData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (Number.isNaN(id)) {
      setError('Mã bài học không hợp lệ')
      return
    }
    setError(null)
    setData(null)
    fetch(`/api/lessons/${id}`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [id])

  if (Number.isNaN(id)) {
    return (
      <p className="text-[var(--coral)]">
        Không tìm thấy bài học.{' '}
        <Link className="font-semibold text-[var(--mint)] underline" to="/lessons">
          Về danh sách
        </Link>
      </p>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-[var(--coral)]/30 bg-[#fff1f2] p-4 shadow-[var(--shadow-card)]">
        <p className="text-[var(--coral)]">{error}</p>
        <Link className="mt-3 inline-block text-sm font-semibold text-[var(--mint)] underline" to="/lessons">
          ← Danh sách bài học
        </Link>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--amber)]" />
        Đang tải chi tiết bài học…
      </div>
    )
  }

  const ic = data.in_class_summary

  return (
    <div className="space-y-5">
      <nav className="text-xs text-[var(--muted)]">
        <Link to="/lessons" className="font-medium text-[var(--mint)] hover:underline">
          Danh sách bài học
        </Link>
        <span className="mx-1.5 opacity-50">/</span>
        <span className="text-[var(--ink)]">Chi tiết</span>
      </nav>

      <header className="space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--amber)]">
          {data.position != null ? `Bài ${data.position}` : 'Bài học'}
        </p>
        <h1 className="font-display text-2xl font-semibold leading-tight text-[var(--ink)] md:text-3xl">
          {data.title}
        </h1>
        {data.desc ? (
          <details className="rounded-lg border border-[var(--border)] bg-[var(--surface)] text-sm [&>summary::-webkit-details-marker]:hidden">
            <summary className="cursor-pointer list-none px-3 py-2 font-medium text-[var(--muted)]">
              Mô tả bài (mở rộng)
            </summary>
            <p className="border-t border-[var(--border)] px-3 py-2 leading-relaxed text-[var(--muted)]">
              {data.desc}
            </p>
          </details>
        ) : null}
        <div className="flex flex-wrap gap-1.5">
          {data.level != null && (
            <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)] px-2 py-0.5 text-[11px] font-semibold text-[var(--mint)]">
              Cấp {data.level}
            </span>
          )}
          {data.last_activity_date && (
            <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--muted)]">
              {data.last_activity_date}
            </span>
          )}
        </div>
      </header>

      <section className="flex flex-wrap gap-x-4 gap-y-1 rounded-xl border border-[var(--border)] bg-[var(--mint-soft)]/40 px-3 py-2.5 text-xs">
        <span className="font-semibold text-[var(--ink)]">Trong lớp:</span>
        <span className="text-[var(--muted)]">
          Phát âm <strong className="text-[var(--ink)]">{ic.pronunciation_drills}</strong>
        </span>
        <span className="text-[var(--muted)]">·</span>
        <span className="text-[var(--muted)]">
          Nói tự do <strong className="text-[var(--ink)]">{ic.free_speaking}</strong>
        </span>
        <span className="text-[var(--muted)]">·</span>
        <span className="text-[var(--muted)]">
          Tương tác <strong className="text-[var(--ink)]">{ic.interactive}</strong>
        </span>
      </section>

      <div className="space-y-3">
        <h2 className="font-display text-sm font-semibold text-[var(--ink)]">Bài tập &amp; luyện tập (LMS)</h2>
        <PracticeBlockPanel label="Bài tập" block={data.homework.bai_tap} />
        <PracticeBlockPanel label="Luyện tập" block={data.homework.luyen_tap} />
      </div>
    </div>
  )
}
