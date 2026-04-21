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

function PracticeSection({
  label,
  subtitle,
  block,
}: {
  label: string
  subtitle: string
  block: PracticeBlock | null
}) {
  if (!block || !block.questions?.length) {
    return (
      <section className="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--elevated)]/50 p-6">
        <h3 className="font-display text-lg font-semibold text-[var(--ink)]">{label}</h3>
        <p className="mt-1 text-sm text-[var(--muted)]">{subtitle}</p>
        <p className="mt-4 text-sm text-[var(--muted)]">Chưa có dữ liệu câu hỏi trong export.</p>
      </section>
    )
  }

  const pct =
    block.total != null && block.total > 0 && block.correct != null
      ? Math.round((block.correct / block.total) * 100)
      : null

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-xl font-semibold text-[var(--ink)]">{label}</h3>
          <p className="mt-1 text-sm text-[var(--muted)]">{subtitle}</p>
        </div>
        <div className="text-right text-sm">
          {block.submitted_date && (
            <p className="tabular-nums text-[var(--muted)]">Nộp: {block.submitted_date}</p>
          )}
          {block.score != null && (
            <p className="mt-1 font-semibold text-[var(--mint)]">
              Điểm: {(block.score * 100).toFixed(0)}%
              {pct != null && (
                <span className="ml-2 font-normal text-[var(--muted)]">
                  ({block.correct}/{block.total})
                </span>
              )}
            </p>
          )}
        </div>
      </div>

      <ol className="mt-6 space-y-4 border-t border-[var(--border)] pt-6">
        {block.questions.map((q, i) => (
          <li
            key={q.question_id ?? i}
            className="rounded-2xl border border-[var(--border)] bg-[var(--void)]/80 p-4 transition hover:border-[var(--mint)]/30"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-display tabular-nums text-[var(--muted)]">{i + 1}.</span>
              {q.question_type && (
                <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 font-medium text-sky-900">
                  {q.question_type}
                </span>
              )}
              {q.requires_media && (
                <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-violet-900">
                  Có media
                </span>
              )}
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[var(--ink)]">{q.question_text}</p>
            {q.correct_answer && (
              <p className="mt-2 text-xs text-[var(--muted)]">
                <span className="font-semibold text-[var(--ink)]">Gợi ý đáp án:</span>{' '}
                <span className="break-words">{q.correct_answer}</span>
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
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
      <div className="rounded-3xl border border-[var(--coral)]/30 bg-[#fff1f2] p-6 shadow-[var(--shadow-card)]">
        <p className="text-[var(--coral)]">{error}</p>
        <Link className="mt-4 inline-block text-sm font-semibold text-[var(--mint)] underline" to="/lessons">
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

  return (
    <div className="space-y-10">
      <nav className="animate-rise text-sm text-[var(--muted)]">
        <Link to="/lessons" className="font-medium text-[var(--mint)] hover:underline">
          Danh sách bài học
        </Link>
        <span className="mx-2 opacity-60">/</span>
        <span className="text-[var(--ink)]">Chi tiết</span>
      </nav>

      <header className="animate-rise space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
          {data.position != null ? `Bài ${data.position}` : 'Bài học'}
        </p>
        <h1 className="font-display text-3xl font-semibold text-[var(--ink)] md:text-4xl">
          {data.title}
        </h1>
        {data.desc ? (
          <p className="max-w-3xl text-sm leading-relaxed text-[var(--muted)] line-clamp-4 md:line-clamp-none">
            {data.desc}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          {data.level != null && (
            <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)] px-3 py-1 text-xs font-semibold text-[var(--mint)]">
              Cấp {data.level}
            </span>
          )}
          {data.last_activity_date && (
            <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-3 py-1 text-xs tabular-nums text-[var(--muted)]">
              Hoạt động gần nhất: {data.last_activity_date}
            </span>
          )}
        </div>
      </header>

      <section className="animate-rise rounded-2xl border border-[var(--border)] bg-[var(--mint-soft)]/50 p-5">
        <h2 className="font-display text-sm font-semibold text-[var(--ink)]">Trong lớp (tóm tắt)</h2>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-[var(--muted)]">Phát âm</dt>
            <dd className="font-semibold text-[var(--ink)]">
              {data.in_class_summary.pronunciation_drills} mục
            </dd>
          </div>
          <div>
            <dt className="text-[var(--muted)]">Nói tự do</dt>
            <dd className="font-semibold text-[var(--ink)]">
              {data.in_class_summary.free_speaking} câu
            </dd>
          </div>
          <div>
            <dt className="text-[var(--muted)]">Tương tác</dt>
            <dd className="font-semibold text-[var(--ink)]">
              {data.in_class_summary.interactive} hoạt động
            </dd>
          </div>
        </dl>
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <PracticeSection
          label="Bài tập"
          subtitle="Theo dõi từ LMS — thường là bài nộp đầu tiên"
          block={data.homework.bai_tap}
        />
        <PracticeSection
          label="Luyện tập"
          subtitle="Bài luyện thứ hai (nếu có trong export)"
          block={data.homework.luyen_tap}
        />
      </div>
    </div>
  )
}
