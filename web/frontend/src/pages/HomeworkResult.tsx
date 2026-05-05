import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { HomeworkQuestionFullDetail, type HomeworkQuestionFull } from '../components/HomeworkQuestionFullDetail'
import { InlineAudioPlayer } from '../components/InlineAudioPlayer'
import { formatActivityDateDisplay } from '../lib/activityDate'
import { formatStudentAnswerDisplay } from '../lib/formatStudentAnswer'
import { lmsQuestionOutcome } from '../lib/lmsQuestionAttempt'

interface SpeakingItem {
  lms_type?: 'free_speaking' | 'conversation' | string | null
  question: string | null
  question_type?: string | null
  expected_answer?: string | null
  user_transcript?: string | null
  score?: number | null
  grammar_score?: number | null
  pronunciation_score?: number | null
  answer_type?: string | null
  timestamp?: string | null
  audio_url?: string | null
  reaction_time_ms?: number | null
  /** When API injects evidence from another lesson to match speaking_evidence */
  cross_lesson_id?: number | null
  cross_lesson_title?: string | null
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
  /** Fragment of student's speaking transcript cited in reason. Null = not cited. */
  speaking_evidence?: string | null
  student_context: StudentContext | null
  /** Gộp từ questions_export + failed_text_questions (API homework). */
  lms_question?: HomeworkQuestionFull | null
}

interface HomeworkModelRun {
  diagnostic: string
  homework: Question[]
  updated_at?: string
}

interface HomeworkData {
  homework: Question[]
  diagnostic: string
  last_run_model?: string
  models?: Record<string, HomeworkModelRun>
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

function normSpeakingText(s: string): string {
  return s
    .replace(/[\u2018\u2019\u02BC]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .toLowerCase()
    .trim()
}

/** Align with backend — short fragments like “no” must not match inside “not”. */
function transcriptMatchesSpeakingEvidence(transcript: string | null | undefined, evidence: string): boolean {
  const t = normSpeakingText(transcript ?? '')
  const ev = normSpeakingText(evidence)
  if (!ev || !t) return false
  const evCore = ev.replace(/[.!?,;:]+$/, '')
  const tCore = t.replace(/[.!?,;:]+$/, '')
  if (evCore === tCore) return true
  if (t.includes(ev)) return true
  if (evCore.length >= 4 && t.includes(evCore)) return true
  if (evCore.length <= 3) {
    const re = new RegExp(`(?<![a-z])${evCore.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z])`, 'i')
    return re.test(t)
  }
  return t.includes(evCore)
}

function formatReactionSec(ms: number | null | undefined): string | null {
  if (ms == null || Number.isNaN(ms)) return null
  return `${(ms / 1000).toFixed(1).replace('.', ',')}s`
}

function scoreBgHw(score: number | null | undefined, max = 100): string {
  if (score == null) return 'bg-slate-200/80'
  const r = score / max
  if (r >= 0.8) return 'bg-emerald-400'
  if (r >= 0.6) return 'bg-amber-400'
  return 'bg-rose-400'
}

function scoreColorHw(score: number | null | undefined, max = 100): string {
  if (score == null) return 'text-[var(--muted)]'
  const r = score / max
  if (r >= 0.8) return 'text-emerald-600'
  if (r >= 0.6) return 'text-amber-500'
  return 'text-rose-500'
}

function ScoreMiniBarHw({ score, max = 100, label }: { score: number | null; max?: number; label: string }) {
  const pct = score != null ? Math.round((score / max) * 100) : 0
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-14 shrink-0 text-[10px] text-[var(--muted)]">{label}</span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--border)]">
        <div
          className={`h-full rounded-full ${scoreBgHw(score, max)}`}
          style={{ width: score != null ? `${pct}%` : '0%' }}
        />
      </div>
      <span className={`w-8 shrink-0 text-right text-[10px] font-semibold tabular-nums ${scoreColorHw(score, max)}`}>
        {score != null ? score : '—'}
      </span>
    </div>
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
  const byText = ctx.failed_text_questions.find(
    (item) => normalizeText(item.question_text) === qNorm,
  )
  if (byText) return byText
  // Fallback: show any failed question from this lesson as supporting evidence
  // (agent may have selected a different question from the same lesson but cited
  //  the homework error in its reason — still relevant context for the learner).
  return ctx.failed_text_questions[0]
}

/** Không lặp khối "đáp án học sinh" khi khối LMS đã có bài làm / cùng question_id */
function shouldHideTextSnippet(q: Question, textItem: FailedTextQuestion | null): boolean {
  if (!textItem || !q.lms_question) return false
  const lms = q.lms_question
  const isSameQuestion =
    lms.question_id != null && textItem.question_id === lms.question_id
  // Only hide when it's the exact same question AND the LMS block already shows the answer.
  // If the textItem is a different (failed) question from the same lesson, always show it —
  // it's independent evidence of a homework error not captured in the selected question.
  if (!isSameQuestion) return false
  const lmsAns = formatStudentAnswerDisplay(lms.student_answer)
  return lmsAns.length > 0
}

function speakingKind(item: SpeakingItem): 'conversation' | 'free_speaking' {
  const t = (item.lms_type ?? '').toLowerCase()
  if (t === 'conversation') return 'conversation'
  return 'free_speaking'
}

function speakingKindUi(kind: ReturnType<typeof speakingKind>): {
  label: string
  rail: string
  badge: string
} {
  switch (kind) {
    case 'conversation':
      return {
        label: 'Hội thoại AI',
        rail: 'bg-violet-500',
        badge: 'border-violet-200/90 bg-violet-50 text-violet-950',
      }
    default:
      return {
        label: 'Nói mở',
        rail: 'bg-orange-500',
        badge: 'border-orange-200/90 bg-orange-50 text-orange-950',
      }
  }
}

/** Bối cảnh đã học — layout gọn: tóm tắt trên cùng, transcript nổi bật, chi tiết trong <details>. */
function PriorLearningContext({ q, studentId }: { q: Question; studentId: string }) {
  const ctx = q.student_context
  if (!ctx) {
    return (
      <p className="text-[12px] text-[var(--muted)]">
        Chưa có ngữ cảnh ưu tiên cho bài này (chạy lại preprocess sau khi có dữ liệu).
      </p>
    )
  }

  const allSpeakingItems = ctx.worst_speaking_items ?? []
  const textItem = findMatchingTextQuestion(q)
  const hideTextSnippet = shouldHideTextSnippet(q, textItem)
  const textItemIsSameQuestion =
    textItem != null &&
    q.lms_question?.question_id != null &&
    textItem.question_id === q.lms_question.question_id

  // When speaking_evidence is set: show only the matched item(s) — no fallback to all items,
  // since unmatched local items are unrelated to the cited evidence (different lesson or wrong evidence).
  // When speaking_evidence is absent: show all items for speaking questions only.
  const speakingEvidence = q.speaking_evidence ?? null
  const speakingItems = (() => {
    if (!speakingEvidence) {
      // No explicit citation → only show for speaking questions
      return q.skill_category === 'speaking' ? allSpeakingItems : []
    }
    return allSpeakingItems.filter(
      (item) => transcriptMatchesSpeakingEvidence(item.user_transcript, speakingEvidence),
    )
  })()

  const hasSnippet = speakingItems.length > 0 || (textItem && !hideTextSnippet)
  const days = ctx.days_since_last_practice
  const firstSpeaking = speakingItems[0] ?? null
  const lastReviewFmt =
    formatActivityDateDisplay(ctx.last_activity_date ?? null) ??
    (firstSpeaking?.timestamp
      ? formatActivityDateDisplay(String(firstSpeaking.timestamp))
      : null)

  const hasTimeContext = lastReviewFmt != null || days !== null
  const evidenceCount =
    speakingItems.length + (textItem && !hideTextSnippet ? 1 : 0)

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--border)] bg-[var(--elevated)]/55 px-3 py-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
            <svg className="h-3.5 w-3.5 shrink-0 text-[var(--mint)]" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-semibold text-[var(--ink)]">Hoạt động gần nhất</span>
            <span className="hidden sm:inline">·</span>
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
        </div>

        {evidenceCount > 0 && (
          <span className="ml-auto inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[10px] font-semibold tabular-nums text-[var(--muted)]">
            {evidenceCount}
            {' '}
            bằng chứng
          </span>
        )}
      </div>

      <div className="divide-y divide-[var(--border)]/80">
        {speakingItems.map((speakingItem, idx) => {
          const kind = speakingKind(speakingItem)
          const ui = speakingKindUi(kind)
          const isConvo = kind === 'conversation'
          const atRaw = speakingItem.answer_type ?? ''
          const at = atRaw.toLowerCase()
          const scoreLine =
            speakingItem.score != null ? `${Math.round(speakingItem.score)}/100` : '—'

          return (
            <div
              key={`${kind}-${speakingItem.timestamp ?? 'x'}-${idx}`}
              className="px-3 py-2.5"
            >
              <div className="flex gap-2.5">
                <div className={`mt-0.5 h-full min-h-[2.25rem] w-1 shrink-0 rounded-full ${ui.rail}`} aria-hidden />

                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${ui.badge}`}>
                      {ui.label}
                    </span>
                    {speakingItem.cross_lesson_title ? (
                      <span className="max-w-[14rem] truncate rounded-md border border-amber-200/90 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-950" title={speakingItem.cross_lesson_title ?? undefined}>
                        Bài khác:
                        {' '}
                        {speakingItem.cross_lesson_title}
                      </span>
                    ) : null}
                    <span className="text-[11px] tabular-nums text-[var(--ink)]">
                      <span className="text-[var(--muted)]">Điểm </span>
                      <span className="font-semibold">{scoreLine}</span>
                    </span>
                    {atRaw ? (
                      <span className="rounded-md bg-[var(--void)] px-1.5 py-0.5 text-[10px] capitalize text-[var(--muted)]">
                        {atRaw.replaceAll('_', ' ')}
                      </span>
                    ) : null}
                    {speakingItem.timestamp ? (
                      <span className="ml-auto hidden text-[10px] tabular-nums text-[var(--muted)] sm:inline">
                        {speakingItem.timestamp}
                      </span>
                    ) : null}
                  </div>

                  {speakingItem.question ? (
                    <p
                      className="text-[11px] leading-snug text-[var(--muted)] line-clamp-2"
                      title={speakingItem.question ?? undefined}
                    >
                      Gợi ý:
                      {' '}
                      <span className="italic text-[var(--ink)]/90">&ldquo;{speakingItem.question}&rdquo;</span>
                    </p>
                  ) : null}

                  <figure className="rounded-lg border border-[var(--border)] bg-[var(--void)] px-2.5 py-2">
                    <figcaption className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                      Học sinh đã nói
                    </figcaption>
                    <blockquote className="mt-1 text-[13px] leading-snug text-[var(--ink)]">
                      &ldquo;{speakingItem.user_transcript ?? '—'}&rdquo;
                    </blockquote>
                  </figure>

                  <details className="group rounded-lg border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-2 py-1.5 text-[11px] font-semibold text-[var(--muted)] transition hover:bg-[var(--elevated)]/60">
                      <span>Chi tiết hoạt động</span>
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

                    <div className="space-y-2 border-t border-[var(--border)]/80 px-2 pb-2 pt-2">
                      <p className="text-[10px] leading-snug text-[var(--muted)]">
                        {isConvo
                          ? 'Điểm tổng / ngữ pháp / phát âm (khi có dữ liệu).'
                          : 'Nói mở theo gợi ý trên lớp — đoạn được chọn để ôn (ưu tiên).'}
                      </p>

                      {isConvo && speakingItem.expected_answer ? (
                        <p className="rounded-md border border-emerald-200 bg-emerald-50/80 px-2 py-1 text-[11px] text-emerald-950">
                          <span className="font-semibold">Câu mẫu: </span>
                          {speakingItem.expected_answer}
                        </p>
                      ) : null}


                      {isConvo ? (
                        <div className="space-y-1">
                          {speakingItem.score != null && <ScoreMiniBarHw score={speakingItem.score} label="Tổng" />}
                          {speakingItem.grammar_score != null && (
                            <ScoreMiniBarHw score={speakingItem.grammar_score} label="Ngữ pháp" />
                          )}
                          {speakingItem.pronunciation_score != null && (
                            <ScoreMiniBarHw score={speakingItem.pronunciation_score} label="Phát âm" />
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-[var(--muted)]">
                          <span>
                            Loại:
                            {' '}
                            <span className="font-semibold capitalize text-[var(--ink)]">{at || '—'}</span>
                          </span>
                          {speakingItem.timestamp ? (
                            <>
                              <span aria-hidden>·</span>
                              <span className="tabular-nums">{speakingItem.timestamp}</span>
                            </>
                          ) : null}
                        </div>
                      )}

                      {(speakingItem.reaction_time_ms != null || speakingItem.audio_url) && (
                        <div className="space-y-1.5 text-[10px] text-[var(--muted)]">
                          {speakingItem.reaction_time_ms != null ? (
                            <p>
                              Phản xạ:
                              {' '}
                              <strong className="tabular-nums text-[var(--ink)]">
                                {formatReactionSec(speakingItem.reaction_time_ms) ?? '—'}
                              </strong>
                            </p>
                          ) : null}
                          {speakingItem.audio_url ? <InlineAudioPlayer src={speakingItem.audio_url} /> : null}
                        </div>
                      )}
                    </div>
                  </details>
                </div>
              </div>
            </div>
          )
        })}

        {textItem && !hideTextSnippet && (
          <div className="flex gap-2.5 px-3 py-2.5">
            <div className="mt-0.5 h-full min-h-[2.25rem] w-1 shrink-0 rounded-full bg-[var(--coral)]" aria-hidden />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-rose-200/90 bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold text-rose-950">
                  {textItemIsSameQuestion ? 'LMS · Sai trước đó' : 'BT về nhà · Câu liên quan'}
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                  {textItemIsSameQuestion ? 'So sánh nhanh' : 'Lỗi cùng bài học'}
                </span>
              </div>
              {!textItemIsSameQuestion && (
                <p className="text-[11px] leading-snug text-[var(--muted)]">
                  {textItem.question_text.length > 90
                    ? textItem.question_text.slice(0, 90) + '…'
                    : textItem.question_text}
                </p>
              )}
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[13px] leading-snug">
                <span className="font-semibold text-[var(--coral)]">
                  {Array.isArray(textItem.student_answer)
                    ? textItem.student_answer.join(', ')
                    : textItem.student_answer}
                </span>
                <span className="text-[11px] text-[var(--muted)]">→</span>
                <span className="font-semibold text-emerald-900">{textItem.correct_answer}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {!hasSnippet && !hasTimeContext && (
        <p className="border-t border-[var(--border)]/80 px-3 py-2.5 text-[11px] leading-relaxed text-[var(--muted)]">
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
  const [activeModel, setActiveModel] = useState<string | null>(null)

  useEffect(() => {
    if (!studentId) return
    setData(null)
    setError(null)
    fetch(`/api/students/${studentId}/homework`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [studentId])

  useEffect(() => {
    const models = data?.models
    if (!models) return
    const keys = Object.keys(models)
    if (keys.length === 0) return
    setActiveModel((prev) => {
      if (prev && models[prev]) return prev
      const preferred = data?.last_run_model
      if (preferred && models[preferred]) return preferred
      return keys[0]
    })
  }, [data])

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

  const modelBlock =
    activeModel && data.models && data.models[activeModel] ? data.models[activeModel] : null
  const displayHomework = modelBlock?.homework ?? data.homework
  const displayDiagnostic = modelBlock?.diagnostic ?? data.diagnostic
  const modelKeys = data.models ? Object.keys(data.models) : []

  return (
    <div className="hw-results-page animate-rise mx-auto space-y-6 pb-12">
      <header className="hw-results-hero flex flex-wrap items-start justify-between gap-3">
        <div className="relative z-[1] max-w-xl">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--amber)]">
            Phiếu giao bài
          </p>
          {modelKeys.length > 1 && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <label className="text-[11px] text-[var(--muted)]" htmlFor="hw-model-pick">
                Phiên bản theo model
              </label>
              <select
                id="hw-model-pick"
                value={activeModel ?? modelKeys[0] ?? ''}
                onChange={(e) => setActiveModel(e.target.value)}
                className="max-w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 text-xs text-[var(--ink)]"
              >
                {modelKeys.map((id) => {
                  const u = data.models?.[id]?.updated_at
                  return (
                    <option key={id} value={id}>
                      {id}
                      {u ? ` — ${u}` : ''}
                    </option>
                  )
                })}
              </select>
            </div>
          )}
          <h1 className="font-display mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)] md:text-3xl">
            {displayHomework.length} câu được chọn
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
            {displayDiagnostic}
          </p>
        </section>
      )}

      <ol className="space-y-5">
        {displayHomework.map((q, i) => {
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
