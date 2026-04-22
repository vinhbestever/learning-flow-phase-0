import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

// ── Types ──────────────────────────────────────────────────────────────── //

interface PronunciationDrill {
  expected_transcript: string
  question_prompt: string | null
}

interface FreeSpeakingQuestion {
  question: string
  question_type: string | null
}

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
  total: number | null
  questions: QuestionRow[]
}

interface InClass {
  pronunciation_drills: PronunciationDrill[]
  free_speaking_questions: FreeSpeakingQuestion[]
}

interface Homework {
  bai_tap: PracticeBlock | null
  luyen_tap: PracticeBlock | null
}

interface LessonContentData {
  lesson_id: number
  title: string | null
  level: number | null
  position: number | null
  desc: string
  in_class: InClass
  homework: Homework
}

// ── Helpers ────────────────────────────────────────────────────────────── //

async function errorMessage(r: Response): Promise<string> {
  try {
    const e = await r.json()
    if (typeof e.detail === 'string') return e.detail
    if (Array.isArray(e.detail))
      return e.detail.map((x: { msg?: string }) => x.msg ?? '').filter(Boolean).join(', ')
  } catch { /* ignore */ }
  return r.statusText || 'Lỗi không xác định'
}

// ── Sub-components ─────────────────────────────────────────────────────── //

function PronunciationSection({ drills }: { drills: PronunciationDrill[] }) {
  if (!drills.length) return (
    <p className="text-sm italic text-[var(--muted)]">Không có bài phát âm.</p>
  )
  return (
    <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden" open>
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
        <span>Phát âm ({drills.length} câu)</span>
        <span className="text-xs font-normal text-[var(--muted)]">▾</span>
      </summary>
      <ul className="max-h-72 divide-y divide-[var(--border)] overflow-y-auto border-t border-[var(--border)]">
        {drills.map((d, i) => (
          <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-sm">
            <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
            <div className="min-w-0">
              <p className="font-medium text-[var(--ink)]">{d.expected_transcript}</p>
              {d.question_prompt && (
                <p className="mt-0.5 text-xs italic text-[var(--muted)]">{d.question_prompt}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}

function FreeSpeakingSection({ questions }: { questions: FreeSpeakingQuestion[] }) {
  if (!questions.length) return (
    <p className="text-sm italic text-[var(--muted)]">Không có câu hỏi nói tự do.</p>
  )
  return (
    <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden" open>
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
        <span>Nói tự do ({questions.length} câu)</span>
        <span className="text-xs font-normal text-[var(--muted)]">▾</span>
      </summary>
      <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
        {questions.map((q, i) => (
          <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-sm">
            <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
            <div className="min-w-0 flex-1">
              <p className="text-[var(--ink)]">{q.question}</p>
              {q.question_type && (
                <span className="mt-1 inline-block rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-800">
                  {q.question_type}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}

function QuestionSection({ label, block }: { label: string; block: PracticeBlock | null }) {
  if (!block) return (
    <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--elevated)]/40 px-4 py-3 text-sm text-[var(--muted)]">
      <span className="font-medium text-[var(--ink)]">{label}:</span> không có dữ liệu.
    </div>
  )
  const questions = block.questions ?? []
  return (
    <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden" open>
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
        <span>{label} ({questions.length} câu)</span>
        <span className="text-xs font-normal text-[var(--muted)]">▾</span>
      </summary>
      {questions.length === 0 ? (
        <p className="border-t border-[var(--border)] px-4 py-3 text-sm italic text-[var(--muted)]">Không có câu hỏi.</p>
      ) : (
        <ul className="max-h-96 divide-y divide-[var(--border)] overflow-y-auto border-t border-[var(--border)]">
          {questions.map((q, i) => (
            <li key={q.question_id ?? i} className="px-4 py-3 text-sm">
              <div className="flex items-start gap-2">
                <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap gap-1">
                    {q.question_type && (
                      <span className="rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-900">
                        {q.question_type}
                      </span>
                    )}
                    {q.requires_media && (
                      <span className="rounded border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[10px] text-violet-900">
                        media
                      </span>
                    )}
                  </div>
                  {q.question_text && (
                    <p className="leading-snug text-[var(--ink)]">{q.question_text}</p>
                  )}
                  {q.correct_answer && (
                    <p className="text-xs text-emerald-700">
                      <span className="font-semibold">Đáp án: </span>{q.correct_answer}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </details>
  )
}

// ── Page ───────────────────────────────────────────────────────────────── //

export default function LessonDetail() {
  const { studentId, lessonId } = useParams<{ studentId: string; lessonId: string }>()
  const id = lessonId ? parseInt(lessonId, 10) : NaN
  const [data, setData] = useState<LessonContentData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'inclass' | 'homework'>('inclass')

  useEffect(() => {
    if (Number.isNaN(id)) {
      setError('Mã bài học không hợp lệ')
      return
    }
    if (!studentId) {
      setError('Thiếu mã học sinh')
      return
    }
    setError(null)
    setData(null)
    fetch(`/api/students/${studentId}/lessons/${id}`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [studentId, id])

  if (!studentId || Number.isNaN(id)) {
    return (
      <p className="text-[var(--coral)]">
        Không tìm thấy bài học.{' '}
        <Link className="font-semibold text-[var(--mint)] underline" to="..">
          ← Danh sách bài học
        </Link>
      </p>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-[var(--coral)]/30 bg-[#fff1f2] p-4 shadow-[var(--shadow-card)]">
        <p className="text-[var(--coral)]">{error}</p>
        <Link className="mt-3 inline-block text-sm font-semibold text-[var(--mint)] underline" to="..">
          ← Danh sách bài học
        </Link>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--amber)]" />
        Đang tải nội dung bài học…
      </div>
    )
  }

  const ic = data.in_class
  const hw = data.homework
  const drillCount = ic.pronunciation_drills.length
  const speakingCount = ic.free_speaking_questions.length
  const btCount = hw.bai_tap?.questions.length ?? 0
  const ltCount = hw.luyen_tap?.questions.length ?? 0

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <nav className="text-xs text-[var(--muted)]">
        <Link to=".." className="font-medium text-[var(--mint)] hover:underline">Danh sách bài học</Link>
        <span className="mx-1.5 opacity-50">/</span>
        <span className="text-[var(--ink)]">Nội dung</span>
      </nav>

      {/* Header */}
      <header className="space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--amber)]">
          {data.position != null ? `Bài ${data.position}` : 'Bài học'}
        </p>
        <h1 className="font-display text-2xl font-semibold leading-tight text-[var(--ink)] md:text-3xl">
          {data.title}
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          {data.level != null && (
            <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)] px-2 py-0.5 text-[11px] font-semibold text-[var(--mint)]">
              Cấp {data.level}
            </span>
          )}
        </div>
        {data.desc && (
          <details className="rounded-lg border border-[var(--border)] bg-[var(--surface)] text-sm [&>summary::-webkit-details-marker]:hidden">
            <summary className="cursor-pointer list-none px-3 py-2 font-medium text-[var(--muted)]">
              Nội dung bài (mở rộng)
            </summary>
            <p className="border-t border-[var(--border)] px-3 py-2 leading-relaxed whitespace-pre-line text-[var(--muted)]">
              {data.desc}
            </p>
          </details>
        )}
      </header>

      {/* Tab selector */}
      <div className="flex rounded-xl border border-[var(--border)] bg-[var(--elevated)] p-1 text-sm">
        <button
          onClick={() => setTab('inclass')}
          className={`flex-1 rounded-lg px-3 py-1.5 font-medium transition ${tab === 'inclass' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'}`}
        >
          Trên lớp
          {(drillCount > 0 || speakingCount > 0) && (
            <span className="ml-1.5 text-xs text-[var(--muted)]">{drillCount + speakingCount}</span>
          )}
        </button>
        <button
          onClick={() => setTab('homework')}
          className={`flex-1 rounded-lg px-3 py-1.5 font-medium transition ${tab === 'homework' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'}`}
        >
          Bài tập về nhà
          {(btCount > 0 || ltCount > 0) && (
            <span className="ml-1.5 text-xs text-[var(--muted)]">{btCount + ltCount}</span>
          )}
        </button>
      </div>

      {/* Tab content */}
      {tab === 'inclass' ? (
        <div className="space-y-3">
          <PronunciationSection drills={ic.pronunciation_drills} />
          <FreeSpeakingSection questions={ic.free_speaking_questions} />
        </div>
      ) : (
        <div className="space-y-4">
          <QuestionSection label="Bài tập" block={hw.bai_tap} />
          <QuestionSection label="Luyện tập" block={hw.luyen_tap} />
        </div>
      )}
    </div>
  )
}
