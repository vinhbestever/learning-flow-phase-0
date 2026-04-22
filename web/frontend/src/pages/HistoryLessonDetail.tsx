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

interface SpeakingItem {
  question: string | null
  user_transcript: string | null
  answer_type: string | null
  score: number | null
  timestamp: string | null
}

interface QuestionRow {
  question_id: number | null
  question_folder: string | null
  question_type: string | null
  question_text: string | null
  requires_media: boolean
  correct_answer: string | null
  is_failed: boolean
  student_answer: unknown
}

interface PracticeBlock {
  practice_id: number | null
  score: number | null
  correct: number | null
  total: number | null
  submitted_date: string | null
  questions: QuestionRow[]
}

interface InClass {
  participated: boolean
  is_completed: boolean
  completion_pct: number | null
  session_count: number
  pronunciation_score_avg: number | null
  pronunciation_attempts: number
  free_speaking_score_avg: number | null
  free_speaking_attempts: number
  worst_speaking_items: SpeakingItem[]
  pronunciation_drills: PronunciationDrill[]
  free_speaking_questions: FreeSpeakingQuestion[]
}

interface Homework {
  attempted: boolean
  bai_tap: PracticeBlock | null
  luyen_tap: PracticeBlock | null
  weak_skills: string[]
  skill_breakdown: Record<string, { correct: number; total: number; accuracy: number | null }>
}

interface LessonDetailData {
  lesson_id: number
  title: string | null
  level: number | null
  position: number | null
  desc: string
  last_activity_date: string | null
  status: string | null
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

function scorePct(n: number | null | undefined, max = 1): string {
  if (n == null || Number.isNaN(n)) return '—'
  return `${Math.round((n / max) * 100)}%`
}

function scoreColorClass(score: number | null | undefined, max = 1): string {
  if (score == null) return 'text-[var(--muted)]'
  const r = score / max
  if (r >= 0.8) return 'text-emerald-600'
  if (r >= 0.6) return 'text-amber-500'
  return 'text-rose-500'
}

function answerTypeLabel(type: string | null): { label: string; cls: string } {
  const map: Record<string, { label: string; cls: string }> = {
    correct:           { label: 'Đúng',       cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    accordant:         { label: 'Phù hợp',    cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    incorrect:         { label: 'Sai',        cls: 'bg-rose-50 text-rose-700 border-rose-200' },
    inaccordant:       { label: 'Lạc đề',     cls: 'bg-rose-50 text-rose-700 border-rose-200' },
    lack_of_knowledge: { label: 'Chưa biết',  cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  }
  return map[type ?? ''] ?? { label: type ?? '', cls: 'bg-slate-50 text-slate-600 border-slate-200' }
}

// ── Sub-components ─────────────────────────────────────────────────────── //

function StatChip({ label, value, valueClass = '' }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-center">
      <span className={`text-base font-bold tabular-nums ${valueClass}`}>{value}</span>
      <span className="mt-0.5 text-[10px] text-[var(--muted)]">{label}</span>
    </div>
  )
}

function InClassSection({ data }: { data: InClass }) {
  if (!data.participated) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--elevated)]/40 px-4 py-3 text-sm text-[var(--muted)]">
        Chưa tham gia buổi học trên lớp.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Tổng quan metrics */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatChip
          label="Hoàn thành"
          value={data.is_completed ? '✓ Xong' : `${data.completion_pct ?? 0}%`}
          valueClass={data.is_completed ? 'text-emerald-600' : 'text-amber-500'}
        />
        <StatChip
          label={`Phát âm (${data.pronunciation_attempts} lần)`}
          value={data.pronunciation_score_avg != null ? `${data.pronunciation_score_avg.toFixed(0)}/100` : '—'}
          valueClass={scoreColorClass(data.pronunciation_score_avg, 100)}
        />
        <StatChip
          label={`Nói tự do (${data.free_speaking_attempts} lần)`}
          value={data.free_speaking_score_avg != null ? `${data.free_speaking_score_avg.toFixed(0)}/100` : '—'}
          valueClass={scoreColorClass(data.free_speaking_score_avg, 100)}
        />
        <StatChip
          label="Số buổi"
          value={String(data.session_count)}
        />
      </div>

      {/* Câu nói tự do sai */}
      {data.worst_speaking_items.length > 0 && (
        <details className="overflow-hidden rounded-xl border border-rose-200 bg-rose-50/40 [&>summary::-webkit-details-marker]:hidden" open>
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-rose-700">
            <span>Câu nói cần cải thiện ({data.worst_speaking_items.length})</span>
            <span className="text-xs font-normal">▾</span>
          </summary>
          <ul className="divide-y divide-rose-100 border-t border-rose-200">
            {data.worst_speaking_items.map((w, i) => {
              const atInfo = answerTypeLabel(w.answer_type)
              return (
                <li key={i} className="px-4 py-3 text-sm">
                  {w.question && (
                    <p className="mb-1 italic text-[var(--muted)]">"{w.question}"</p>
                  )}
                  <p className="text-[var(--ink)]">
                    <span className="font-medium text-[var(--muted)]">Học sinh: </span>
                    {w.user_transcript || <span className="text-[var(--muted)]">(không có transcript)</span>}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    {w.answer_type && (
                      <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${atInfo.cls}`}>
                        {atInfo.label}
                      </span>
                    )}
                    {w.timestamp && <span className="text-[10px] text-[var(--muted)]">{w.timestamp}</span>}
                  </div>
                </li>
              )
            })}
          </ul>
        </details>
      )}

      {/* Danh sách phát âm */}
      {data.pronunciation_drills.length > 0 && (
        <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
            <span>Bài phát âm ({data.pronunciation_drills.length} lần luyện)</span>
            <span className="text-xs font-normal text-[var(--muted)]">▾</span>
          </summary>
          <ul className="max-h-60 divide-y divide-[var(--border)] overflow-y-auto border-t border-[var(--border)]">
            {data.pronunciation_drills.map((d, i) => (
              <li key={i} className="flex items-start gap-3 px-4 py-2 text-xs">
                <span className="w-5 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
                <div className="min-w-0">
                  <p className="font-medium text-[var(--ink)]">{d.expected_transcript}</p>
                  {d.question_prompt && (
                    <p className="mt-0.5 text-[var(--muted)] italic">{d.question_prompt}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Câu hỏi nói tự do */}
      {data.free_speaking_questions.length > 0 && (
        <details className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] [&>summary::-webkit-details-marker]:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
            <span>Câu hỏi nói tự do ({data.free_speaking_questions.length})</span>
            <span className="text-xs font-normal text-[var(--muted)]">▾</span>
          </summary>
          <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
            {data.free_speaking_questions.map((q, i) => (
              <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-sm">
                <span className="w-5 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
                <p className="text-[var(--ink)]">{q.question}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

function QuestionList({ questions, attempted = true }: { questions: QuestionRow[]; attempted?: boolean }) {
  if (!questions.length) {
    return <p className="text-sm text-[var(--muted)] italic">Không có câu hỏi.</p>
  }

  const QuestionItem = ({ q, idx }: { q: QuestionRow; idx: number }) => (
    <li>
      <details className={`group [&>summary::-webkit-details-marker]:hidden ${q.is_failed ? 'bg-rose-50/30' : ''}`}>
        <summary className="flex cursor-pointer list-none items-start gap-2 px-3 py-2.5 text-left text-xs">
          <span className="mt-0.5 w-6 shrink-0 tabular-nums text-[var(--muted)]">{idx + 1}.</span>
          <span className="min-w-0 flex-1 space-x-1">
            {q.question_type && (
              <span className="inline-block rounded border border-sky-200 bg-sky-50 px-1 py-0.5 text-[10px] font-medium text-sky-900">
                {q.question_type}
              </span>
            )}
            {q.requires_media && (
              <span className="inline-block rounded border border-violet-200 bg-violet-50 px-1 py-0.5 text-[10px] text-violet-900">
                media
              </span>
            )}
            {q.is_failed && (
              <span className="inline-block rounded border border-rose-200 bg-rose-50 px-1 py-0.5 text-[10px] font-semibold text-rose-700">
                ✗ Sai
              </span>
            )}
            <span className="line-clamp-2 text-[var(--ink)]">{q.question_text}</span>
          </span>
          <span className="shrink-0 text-[10px] text-[var(--muted)]">▼</span>
        </summary>
        <div className="space-y-1.5 border-t border-[var(--border)] bg-[var(--void)]/30 px-3 py-3 pl-11 text-xs leading-relaxed">
          <p className="text-[var(--ink)]">{q.question_text}</p>
          {q.correct_answer && (
            <p>
              <span className="font-semibold text-emerald-700">Đáp án đúng: </span>
              <span className="text-emerald-700">{q.correct_answer}</span>
            </p>
          )}
          {q.is_failed && q.student_answer != null && (
            <p>
              <span className="font-semibold text-rose-600">Học sinh trả lời: </span>
              <span className="text-rose-600">{JSON.stringify(q.student_answer)}</span>
            </p>
          )}
        </div>
      </details>
    </li>
  )

  // Not attempted: show as question bank, not results
  if (!attempted) {
    return (
      <details open className="overflow-hidden rounded-lg border border-slate-200 [&>summary::-webkit-details-marker]:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">
          <span>Ngân hàng câu hỏi ({questions.length} câu)</span>
          <span className="font-normal">▾</span>
        </summary>
        <ul className="divide-y divide-slate-100 border-t border-slate-100">
          {questions.map((q, i) => <QuestionItem key={q.question_id ?? i} q={q} idx={i} />)}
        </ul>
      </details>
    )
  }

  const failed = questions.filter((q) => q.is_failed)
  const passed = questions.filter((q) => !q.is_failed)

  return (
    <div className="space-y-1">
      {failed.length > 0 && (
        <details open className="overflow-hidden rounded-lg border border-rose-200 [&>summary::-webkit-details-marker]:hidden">
          <summary className="cursor-pointer list-none bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
            ✗ Câu làm sai ({failed.length})
          </summary>
          <ul className="divide-y divide-rose-100 border-t border-rose-100">
            {failed.map((q, i) => <QuestionItem key={q.question_id ?? i} q={q} idx={i} />)}
          </ul>
        </details>
      )}
      {passed.length > 0 && (
        <details className="overflow-hidden rounded-lg border border-[var(--border)] [&>summary::-webkit-details-marker]:hidden">
          <summary className="cursor-pointer list-none bg-[var(--elevated)] px-3 py-2 text-xs font-semibold text-[var(--muted)]">
            ✓ Câu làm đúng ({passed.length})
          </summary>
          <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
            {passed.map((q, i) => <QuestionItem key={q.question_id ?? i} q={q} idx={i} />)}
          </ul>
        </details>
      )}
    </div>
  )
}

function PracticePanel({
  label,
  block,
  attempted = true,
}: {
  label: string
  block: PracticeBlock | null
  /** When false, questions are from export only — show as question bank, not pass/fail results. */
  attempted?: boolean
}) {
  if (!block) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--elevated)]/40 px-4 py-3 text-sm text-[var(--muted)]">
        <span className="font-medium text-[var(--ink)]">{label}:</span> chưa làm.
      </div>
    )
  }

  const scoreVal = block.score != null ? Math.round(block.score * 100) : null
  const scoreClass = block.score != null
    ? block.score >= 0.8 ? 'text-emerald-600' : block.score >= 0.6 ? 'text-amber-500' : 'text-rose-500'
    : 'text-[var(--muted)]'
  const barWidth = block.score != null ? `${Math.round(block.score * 100)}%` : '0%'
  const barColor = block.score != null
    ? block.score >= 0.8 ? 'bg-emerald-400' : block.score >= 0.6 ? 'bg-amber-400' : 'bg-rose-400'
    : 'bg-slate-200'

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
        <span className="font-display font-semibold text-[var(--ink)]">{label}</span>
        {scoreVal != null && (
          <>
            <span className={`text-lg font-bold tabular-nums ${scoreClass}`}>{scoreVal}%</span>
            <span className="text-sm text-[var(--muted)]">{block.correct}/{block.total} đúng</span>
          </>
        )}
        {block.submitted_date && (
          <span className="ml-auto text-xs tabular-nums text-[var(--muted)]">Nộp {block.submitted_date}</span>
        )}
      </div>

      {/* Score bar */}
      {block.score != null && (
        <div className="mx-4 mb-3 h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
          <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: barWidth }} />
        </div>
      )}

      {/* Question list */}
      <div className="border-t border-[var(--border)] px-3 pb-3 pt-2">
        <QuestionList questions={block.questions} attempted={attempted} />
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────── //

export default function HistoryLessonDetail() {
  const { studentId, lessonId } = useParams<{ studentId: string; lessonId: string }>()
  const id = lessonId ? parseInt(lessonId, 10) : NaN
  const [data, setData] = useState<LessonDetailData | null>(null)
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

  if (Number.isNaN(id) || !studentId) {
    return (
      <p className="text-[var(--coral)]">
        Không tìm thấy bài học.{' '}
        <Link className="font-semibold text-[var(--mint)] underline" to="..">
          ← Lịch sử học tập
        </Link>
      </p>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-[var(--coral)]/30 bg-[#fff1f2] p-4 shadow-[var(--shadow-card)]">
        <p className="text-[var(--coral)]">{error}</p>
        <Link className="mt-3 inline-block text-sm font-semibold text-[var(--mint)] underline" to="..">
          ← Lịch sử học tập
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

  const hw = data.homework
  const ic = data.in_class

  const statusLabel: Record<string, { label: string; cls: string }> = {
    completed:      { label: 'Hoàn thành',   cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    in_class_only:  { label: 'Chỉ học lớp',  cls: 'bg-sky-50 text-sky-700 border-sky-200' },
    homework_only:  { label: 'Chỉ bài tập',  cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  }
  const statusInfo = statusLabel[data.status ?? ''] ?? { label: data.status ?? '', cls: 'bg-slate-50 text-slate-600 border-slate-200' }

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <nav className="text-xs text-[var(--muted)]">
        <Link to=".." className="font-medium text-[var(--mint)] hover:underline">Lịch sử học tập</Link>
        <span className="mx-1.5 opacity-50">/</span>
        <span className="text-[var(--ink)]">Chi tiết</span>
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
          {data.status && (
            <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusInfo.cls}`}>
              {statusInfo.label}
            </span>
          )}
          {data.last_activity_date && (
            <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--muted)]">
              {data.last_activity_date}
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

      {/* Skill breakdown nhanh */}
      {Object.keys(hw.skill_breakdown).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(hw.skill_breakdown).map(([skill, s]) => (
            <div key={skill} className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs">
              <span className="text-[var(--muted)]">{skill}</span>
              <span className={`font-bold tabular-nums ${scoreColorClass(s.accuracy)}`}>
                {s.accuracy != null ? `${Math.round(s.accuracy * 100)}%` : '—'}
              </span>
              <span className="text-[var(--muted)]">{s.correct}/{s.total}</span>
            </div>
          ))}
        </div>
      )}

      {/* Weak skills */}
      {hw.weak_skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {hw.weak_skills.map((s) => (
            <span key={s} className="rounded border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700">
              ⚠ {s}
            </span>
          ))}
        </div>
      )}

      {/* Tab selector */}
      <div className="flex rounded-xl border border-[var(--border)] bg-[var(--elevated)] p-1 text-sm">
        <button
          onClick={() => setTab('inclass')}
          className={`flex-1 rounded-lg px-3 py-1.5 font-medium transition ${tab === 'inclass' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'}`}
        >
          Trên lớp
          {ic.participated && (
            <span className={`ml-1.5 text-xs ${ic.is_completed ? 'text-emerald-600' : 'text-amber-500'}`}>
              {ic.is_completed ? '✓' : `${ic.completion_pct ?? 0}%`}
            </span>
          )}
        </button>
        <button
          onClick={() => setTab('homework')}
          className={`flex-1 rounded-lg px-3 py-1.5 font-medium transition ${tab === 'homework' ? 'bg-[var(--surface)] text-[var(--ink)] shadow-sm' : 'text-[var(--muted)] hover:text-[var(--ink)]'}`}
        >
          Bài tập về nhà
          {hw.attempted && (() => {
            const scores = [hw.bai_tap?.score, hw.luyen_tap?.score].filter((s): s is number => s != null)
            const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null
            return avg != null ? (
              <span className={`ml-1.5 text-xs ${scoreColorClass(avg)}`}>{scorePct(avg)}</span>
            ) : null
          })()}
        </button>
      </div>

      {/* Tab content */}
      {tab === 'inclass' ? (
        <InClassSection data={ic} />
      ) : (
        <div className="space-y-4">
          <PracticePanel label="Bài tập" block={hw.bai_tap} attempted={hw.attempted} />
          <PracticePanel label="Luyện tập" block={hw.luyen_tap} attempted={hw.attempted} />
        </div>
      )}
    </div>
  )
}
