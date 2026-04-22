import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { HomeworkQuestionFullDetail, type HomeworkQuestionFull } from '../components/HomeworkQuestionFullDetail'
import { formatActivityDateDisplay } from '../lib/activityDate'
import { formatStudentAnswerDisplay } from '../lib/formatStudentAnswer'
import { lmsQuestionOutcome } from '../lib/lmsQuestionAttempt'

interface SpeakingItem {
  question: string
  question_type: string
  user_transcript: string
  score: number
  answer_type: string
  timestamp: string
}

interface FailedTextQuestion {
  practice_id: number
  question_id: number
  question_folder: string
  question_type: string
  question_text: string
  correct_answer: string
  student_answer: string[] | string
  requires_media: boolean
}

interface StudentContext {
  /** ISO-like LMS date when present (requires preprocess after this field was added). */
  last_activity_date?: string | null
  days_since_last_practice: number | null
  worst_speaking_items: SpeakingItem[]
  failed_text_questions: FailedTextQuestion[]
}

interface Question {
  question_no: number
  lesson_id: number
  lesson_title: string
  skill_category: string
  question_type: string
  question_text: string
  correct_answer: string | null
  difficulty: 'easy' | 'medium' | 'hard'
  reason: string
  student_context: StudentContext | null
  /** Gộp từ questions_export + failed_text_questions (API homework). */
  lms_question?: HomeworkQuestionFull | null
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

function normalizeText(s: string) {
  return s.toLowerCase().replace(/\s+/g, ' ').trim()
}

function findMatchingSpeakingItem(q: Question): SpeakingItem | null {
  const ctx = q.student_context
  if (!ctx || !ctx.worst_speaking_items.length) return null
  const qNorm = normalizeText(q.question_text)
  return (
    ctx.worst_speaking_items.find((item) => normalizeText(item.question) === qNorm) ??
    ctx.worst_speaking_items[0]
  )
}

function findMatchingTextQuestion(q: Question): FailedTextQuestion | null {
  const ctx = q.student_context
  if (!ctx || !ctx.failed_text_questions.length) return null
  const qid = q.lms_question?.question_id
  if (qid != null) {
    const byId = ctx.failed_text_questions.find((x) => x.question_id === qid)
    if (byId) return byId
  }
  const qNorm = normalizeText(q.question_text)
  return (
    ctx.failed_text_questions.find((item) => normalizeText(item.question_text) === qNorm) ??
    null
  )
}

/** Không lặp khối “đáp án học sinh” khi khối LMS đã có bài làm / cùng question_id */
function shouldHideTextSnippet(q: Question, textItem: FailedTextQuestion | null): boolean {
  if (!textItem || !q.lms_question) return false
  const lms = q.lms_question
  const lmsAns = formatStudentAnswerDisplay(lms.student_answer)
  if (lmsAns.length > 0) return true
  if (
    lms.question_id != null
    && textItem.question_id === lms.question_id
  ) {
    return true
  }
  return false
}

/** Bối cảnh ưu tiên (lần ôn, transcript / câu chữ bổ sung — không trùng LMS đã hiển thị) */
function PriorLearningContext({ q, studentId }: { q: Question; studentId: string }) {
  const ctx = q.student_context
  if (!ctx) {
    return (
      <p className="text-[12px] text-[var(--muted)]">
        Chưa có ngữ cảnh ưu tiên cho bài này (chạy lại preprocess sau khi có dữ liệu).
      </p>
    )
  }

  const speakingItem = q.skill_category === 'speaking' ? findMatchingSpeakingItem(q) : null
  const textItem = q.skill_category !== 'speaking' ? findMatchingTextQuestion(q) : null
  const hideTextSnippet = shouldHideTextSnippet(q, textItem)

  const hasSnippet = speakingItem || (textItem && !hideTextSnippet)
  const days = ctx.days_since_last_practice
  const lastReviewFmt =
    formatActivityDateDisplay(ctx.last_activity_date ?? null) ??
    (speakingItem?.timestamp
      ? formatActivityDateDisplay(String(speakingItem.timestamp))
      : null)

  const hasTimeContext = lastReviewFmt != null || days !== null

  return (
    <div className="rounded-xl border border-[var(--border)]/80 bg-[var(--void)]/25 px-3 py-3">
      <div className="flex flex-wrap gap-2">
        {(lastReviewFmt || days !== null) && (
          <span className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[11px] text-[var(--muted)]">
            <svg className="h-3 w-3 shrink-0 text-[var(--mint)]" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            Lần ôn / hoạt động:{' '}
            {lastReviewFmt ? (
              <time
                dateTime={lastReviewFmt.dateTime}
                title={lastReviewFmt.title}
                className="font-semibold tabular-nums text-[var(--ink)]"
              >
                {lastReviewFmt.label}
              </time>
            ) : (
              <span className="font-semibold tabular-nums text-[var(--ink)]">{days ?? '—'} ngày</span>
            )}
          </span>
        )}
      </div>

      {speakingItem && (
        <div className="mt-3 rounded-lg border border-orange-200/90 bg-gradient-to-br from-orange-50/95 to-[var(--surface)] px-2.5 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-orange-800">
              Transcript trên lớp (nói)
            </p>
            <span className="rounded border border-orange-300 bg-white/70 px-1.5 py-0.5 text-[9px] font-bold text-orange-900">
              Đã làm — theo lớp
            </span>
          </div>
          <p className="mt-1 text-[10px] leading-snug text-orange-800/90">
            Đoạn được chọn để ôn (ưu tiên), không phải đáp án mẫu hay kết luận “đúng hoàn toàn”.
          </p>
          <p className="mt-1.5 text-[13px] leading-relaxed italic text-[var(--ink)]">
            &ldquo;{speakingItem.user_transcript}&rdquo;
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-orange-700">
            <span>
              Điểm:{' '}
              <span className={`font-bold tabular-nums ${speakingItem.score === 0 ? 'text-[var(--coral)]' : 'text-emerald-600'}`}>
                {speakingItem.score}
              </span>
            </span>
            <span className="text-orange-300">·</span>
            <span className="capitalize">{speakingItem.answer_type}</span>
            <span className="text-orange-300">·</span>
            <span className="tabular-nums opacity-90">{speakingItem.timestamp}</span>
          </div>
        </div>
      )}

      {textItem && !hideTextSnippet && (
        <div className="mt-3 rounded-lg border border-rose-200/90 bg-rose-50/60 px-2.5 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-rose-800">
              Bài làm sai trước đó (LMS)
            </p>
            <span className="rounded border border-rose-300 bg-white/70 px-1.5 py-0.5 text-[9px] font-bold text-rose-900">
              Sai
            </span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-baseline gap-2 text-[13px] leading-snug">
            <span className="font-medium text-[var(--coral)]">
              {Array.isArray(textItem.student_answer)
                ? textItem.student_answer.join(', ')
                : textItem.student_answer}
            </span>
            <span className="text-[11px] text-[var(--muted)]">→ đáp án đúng</span>
            <span className="font-medium text-emerald-800">{textItem.correct_answer}</span>
          </div>
        </div>
      )}

      {!hasSnippet && !hasTimeContext && (
        <p className="mt-2 text-[11px] leading-relaxed text-[var(--muted)]">
          Không có thêm transcript hay câu chữ gắn trực tiếp với ưu tiên này — mở{' '}
          <Link
            className="font-semibold text-[var(--mint)] underline"
            to={`/students/${studentId}/history/${q.lesson_id}`}
          >
            chi tiết bài học
          </Link>
          {' '}để xem đầy đủ.
        </p>
      )}
    </div>
  )
}

export default function HomeworkResult() {
  const { studentId } = useParams<{ studentId: string }>()
  const [data, setData] = useState<HomeworkData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDiag, setShowDiag] = useState(false)

  useEffect(() => {
    if (!studentId) return
    setData(null)
    setError(null)
    fetch(`/api/students/${studentId}/homework`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [studentId])

  if (!studentId) {
    return <p className="text-[var(--muted)]">Thiếu mã học sinh trong URL.</p>
  }

  if (error) {
    return (
      <div className="space-y-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-card)]">
        <p className="text-[var(--coral)]">{error}</p>
        <Link
          to="../generate"
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
    <div className="hw-results-page animate-rise mx-auto space-y-6 pb-12">
      <header className="hw-results-hero flex flex-wrap items-start justify-between gap-3">
        <div className="relative z-[1] max-w-xl">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Phiếu giao bài
          </p>
          <h1 className="font-display mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)] md:text-3xl">
            {data.homework.length} câu được chọn
          </h1>
          <p className="mt-2 text-[12px] leading-relaxed text-[var(--muted)] md:text-[13px]">
            Mỗi thẻ đi theo thứ tự: <span className="font-semibold text-[var(--mint)]">nội dung</span>
            {' '}→ <span className="font-semibold text-[var(--amber)]">lý do giao</span>
            {' '}→ <span className="font-semibold text-[var(--ink)]">bối cảnh đã học</span>. Phần LMS (nếu có) giống trang chi tiết bài học.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowDiag((d) => !d)}
          className="relative z-[1] shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface)]/90 px-3.5 py-2 text-xs font-semibold text-[var(--muted)] shadow-sm transition hover:border-[var(--mint)]/45 hover:text-[var(--ink)]"
        >
          {showDiag ? 'Ẩn đánh giá' : 'Đánh giá đầy đủ'}
        </button>
      </header>

      {showDiag && (
        <section className="max-h-[min(45vh,380px)] overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-card)]">
          <p className="font-display text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
            Diagnostic
          </p>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">
            {data.diagnostic}
          </p>
        </section>
      )}

      <ol className="space-y-5">
        {data.homework.map((q, i) => {
          const lmsOutcome = q.lms_question ? lmsQuestionOutcome(q.lms_question) : null
          return (
          <li
            key={q.question_no}
            className="hw-slip-card animate-rise overflow-hidden"
            style={{ animationDelay: `${Math.min(i, 10) * 0.055}s` }}
          >
            <div className="flex flex-wrap items-center gap-1.5 border-b border-[var(--border)] bg-[var(--void)]/50 px-3 py-2">
              <span className="font-display w-8 text-center text-sm font-bold tabular-nums text-[var(--ink)]">
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
              <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                {q.question_type}
              </span>
              {q.lms_question ? (
                <>
                  <span className="hw-meta-badge">Đề LMS đầy đủ</span>
                  {lmsOutcome === 'correct' && (
                    <span className="rounded-md border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[9px] font-bold text-emerald-900">
                      Làm đúng trên LMS
                    </span>
                  )}
                  {lmsOutcome === 'incorrect' && (
                    <span className="rounded-md border border-rose-300 bg-rose-50 px-2 py-0.5 text-[9px] font-bold text-rose-900">
                      Làm sai trên LMS
                    </span>
                  )}
                  {lmsOutcome === 'not_submitted' && (
                    <span className="rounded-md border border-dashed border-amber-400 bg-amber-50 px-2 py-0.5 text-[9px] font-bold text-amber-950">
                      Chưa làm trên LMS
                    </span>
                  )}
                </>
              ) : q.skill_category === 'speaking' ? (
                <span className="hw-meta-badge border-violet-300 bg-violet-50 text-violet-900">Câu nói</span>
              ) : (
                <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Tóm tắt
                </span>
              )}
              <Link
                to={`/students/${studentId}/history/${q.lesson_id}`}
                className="ml-auto min-w-0 max-w-[min(100%,14rem)] truncate text-right text-[10px] font-semibold text-[var(--mint)] hover:underline md:max-w-[20rem]"
                title="Chi tiết bài trong lịch sử"
              >
                {q.lesson_title}
              </Link>
            </div>

            <div className="hw-slip-inner pr-3">
              {/* 1 · Nội dung (đặt trước — đúng nhận thức đọc) */}
              <section className="pt-4">
                <p className="hw-section-label">1 · Nội dung</p>
                {q.lms_question ? (
                  <HomeworkQuestionFullDetail
                    typeShownAbove={q.question_type}
                    q={{
                      ...q.lms_question,
                      question_text:
                        (q.lms_question.question_text && q.lms_question.question_text.trim())
                          ? q.lms_question.question_text
                          : q.question_text,
                      correct_answer:
                        (q.lms_question.correct_answer != null && String(q.lms_question.correct_answer).trim())
                          ? q.lms_question.correct_answer
                          : q.correct_answer,
                      question_type: q.lms_question.question_type || q.question_type,
                      requires_media: Boolean(q.lms_question.requires_media),
                      question_folder: q.lms_question.question_folder ?? null,
                      question_id: q.lms_question.question_id ?? null,
                    }}
                    index={i}
                    practiceId={q.lms_question.practice_id}
                    questionsSource={q.lms_question.questions_source}
                    attempted
                  />
                ) : q.skill_category === 'speaking' ? (
                  <div className="rounded-xl border-2 border-dashed border-orange-200/90 bg-gradient-to-br from-orange-50/90 via-[var(--surface)] to-[var(--void)] px-3 py-3">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-orange-800">
                      Câu nói tự do
                    </p>
                    <p className="mt-2 text-[15px] font-medium leading-snug text-[var(--ink)]">{q.question_text}</p>
                    <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] text-[var(--muted)]">
                      <span className="h-1.5 w-1.5 rounded-full bg-orange-400" aria-hidden />
                      Đáp án mở — xem transcript ở mục 3
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-[var(--border)] bg-[var(--void)]/30 px-3 py-3">
                    <p className="text-[13px] leading-relaxed text-[var(--ink)] md:text-sm">{q.question_text}</p>
                    {q.correct_answer && q.correct_answer !== 'open' && (
                      <details className="group mt-3 overflow-hidden rounded-lg border border-dashed border-[var(--mint)]/45 bg-[var(--mint-soft)]/35 [&>summary::-webkit-details-marker]:hidden">
                        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-2.5 py-2 text-[11px] font-semibold text-[var(--mint)] transition hover:bg-[var(--mint-soft)]/55">
                          <span>Xem đáp án đúng</span>
                          <svg
                            className="h-3.5 w-3.5 shrink-0 text-[var(--muted)] transition-transform duration-200 group-open:rotate-180"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            aria-hidden
                          >
                            <path
                              fillRule="evenodd"
                              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </summary>
                        <div className="border-t border-[var(--mint)]/25 px-2.5 pb-2.5 pt-2 text-[13px] leading-relaxed text-[var(--ink)]">
                          {q.correct_answer}
                        </div>
                      </details>
                    )}
                  </div>
                )}
              </section>

              <section className="mt-6 border-t border-[var(--border)]/80 pt-5">
                <p className="hw-section-label">2 · Vì sao được chọn</p>
                <p className="text-[13px] font-medium leading-relaxed text-[var(--ink)] md:text-[14px]">
                  {q.reason}
                </p>
              </section>

              <section className="mt-6 border-t border-[var(--border)]/80 pb-4 pt-5">
                <p className="hw-section-label">3 · Bối cảnh đã học</p>
                <PriorLearningContext q={q} studentId={studentId} />
              </section>
            </div>
          </li>
          )
        })}
      </ol>
    </div>
  )
}
