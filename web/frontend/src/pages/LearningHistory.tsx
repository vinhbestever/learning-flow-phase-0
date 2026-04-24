import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CollapsibleModule } from '../components/CollapsibleModule'
import { formatActivityDateDisplay } from '../lib/activityDate'
import { groupHistoryByMonth } from '../lib/lessonGroups'

interface SpeakingItem {
  lms_type?: 'free_speaking' | 'brainstorm' | 'conversation' | string | null
  question: string | null
  expected_answer?: string | null
  target_objects?: string[] | null
  user_transcript: string | null
  answer_type: string | null
  score: number | null
  grammar_score?: number | null
  pronunciation_score?: number | null
  correct_objects?: string[] | null
  timestamp: string | null
}

interface FailedQuestion {
  question_type: string | null
  question_text: string
  correct_answer: string | null
  student_answer: unknown
}

interface PracticeResult {
  practice_id: number
  score: number
  correct: number
  total: number
  submitted_date: string | null
}

interface SessionMetricsLite {
  cups?: number | null
  audio_turns?: number | null
  avg_reaction_ms?: number | null
  fastest_reaction_ms?: number | null
  session_status?: string | null
}

interface InClassSummary {
  participated: boolean
  is_completed: boolean
  completion_pct: number | null
  session_count: number
  pronunciation_score_avg: number | null
  pronunciation_attempts: number
  free_speaking_score_avg: number | null
  free_speaking_attempts: number
  brainstorm_score_avg?: number | null
  brainstorm_attempts?: number
  conversation_score_avg?: number | null
  conversation_attempts?: number
  session_metrics?: SessionMetricsLite | null
  worst_speaking_items: SpeakingItem[]
}

interface HomeworkSummary {
  attempted: boolean
  bai_tap: PracticeResult | null
  luyen_tap: PracticeResult | null
  weak_skills: string[]
  failed_text_count: number
  failed_media_count: number
  failed_text_questions: FailedQuestion[]
}

interface HistoryItem {
  lesson_id: number
  title: string | null
  level: number | null
  status: string
  last_activity_date: string | null
  days_since_last_practice: number | null
  forgetting_score: number | null
  weakness_score: number | null
  composite_priority_score: number | null
  in_class: InClassSummary
  homework: HomeworkSummary
}

interface HistoryResponse {
  student_id: number | string | null
  reference_date: string | null
  count: number
  items: HistoryItem[]
}

async function errorMessage(r: Response): Promise<string> {
  try {
    const e = await r.json()
    if (typeof e.detail === 'string') return e.detail
    if (Array.isArray(e.detail))
      return e.detail.map((x: { msg?: string }) => x.msg ?? '').filter(Boolean).join(', ')
  } catch { /* ignore */ }
  return r.statusText || 'Lỗi không xác định'
}

function pct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return `${(n * 100).toFixed(0)}%`
}

function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'text-[var(--muted)]'
  if (score >= 0.8) return 'text-emerald-600'
  if (score >= 0.6) return 'text-amber-500'
  return 'text-rose-500'
}

function answerTypeBadge(type: string | null): string {
  if (!type) return ''
  const map: Record<string, string> = {
    correct: 'Đúng',
    incorrect: 'Sai',
    inaccordant: 'Lạc đề',
    accordant: 'Phù hợp',
    lack_of_knowledge: 'Chưa biết',
  }
  return map[type] ?? type
}

function scoreColor100(score: number | null | undefined): string {
  if (score == null) return 'text-[var(--muted)]'
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-amber-500'
  return 'text-rose-500'
}

function formatReactionMs(ms: number | null | undefined): string | null {
  if (ms == null || Number.isNaN(ms)) return null
  return `${(ms / 1000).toFixed(1).replace('.', ',')}s`
}

function PracticeRow({ label, result }: { label: string; result: PracticeResult | null }) {
  if (!result) return (
    <div className="flex items-center gap-2 text-[11px] text-[var(--muted)]">
      <span className="w-16 shrink-0 font-semibold">{label}</span>
      <span>—</span>
    </div>
  )
  const pctVal = Math.round(result.score * 100)
  const colorClass = result.score >= 0.8 ? 'text-emerald-600' : result.score >= 0.6 ? 'text-amber-500' : 'text-rose-500'
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-16 shrink-0 font-semibold text-[var(--muted)]">{label}</span>
      <span className={`font-bold tabular-nums ${colorClass}`}>{pctVal}%</span>
      <span className="text-[var(--muted)]">{result.correct}/{result.total} đúng</span>
      {result.submitted_date && (
        <span className="ml-auto text-[var(--muted)]">{result.submitted_date}</span>
      )}
    </div>
  )
}

function InClassPanel({ data }: { data: InClassSummary }) {
  if (!data.participated) {
    return <p className="text-[11px] text-[var(--muted)] italic">Chưa tham gia lớp học.</p>
  }
  return (
    <div className="space-y-2">
      {/* Tổng quan */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
        <span className={data.is_completed ? 'text-emerald-600 font-semibold' : 'text-amber-500 font-semibold'}>
          {data.is_completed ? '✓ Hoàn thành' : `${data.completion_pct ?? 0}% hoàn thành`}
        </span>
        {data.session_count > 1 && (
          <span className="text-[var(--muted)]">{data.session_count} buổi</span>
        )}
      </div>

      {/* Điểm kỹ năng */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
        {data.pronunciation_attempts > 0 && (
          <div className="flex items-baseline gap-1 text-[11px]">
            <span className="text-[var(--muted)]">Phát âm</span>
            <span className={`font-bold tabular-nums ${scoreColor(data.pronunciation_score_avg != null ? data.pronunciation_score_avg / 100 : null)}`}>
              {data.pronunciation_score_avg != null ? `${data.pronunciation_score_avg.toFixed(0)}/100` : '—'}
            </span>
            <span className="text-[var(--muted)]">({data.pronunciation_attempts} lần)</span>
          </div>
        )}
        {(data.brainstorm_attempts ?? 0) > 0 && (
          <div className="flex items-baseline gap-1 text-[11px]">
            <span className="text-[var(--muted)]">Brainstorm</span>
            <span className={`font-bold tabular-nums ${scoreColor(data.brainstorm_score_avg != null ? data.brainstorm_score_avg / 100 : null)}`}>
              {data.brainstorm_score_avg != null ? `${data.brainstorm_score_avg.toFixed(0)}/100` : '—'}
            </span>
            <span className="text-[var(--muted)]">({data.brainstorm_attempts} lần)</span>
          </div>
        )}
        {data.free_speaking_attempts > 0 && (
          <div className="flex items-baseline gap-1 text-[11px]">
            <span className="text-[var(--muted)]">Nói mở / warmup</span>
            <span className={`font-bold tabular-nums ${scoreColor(data.free_speaking_score_avg != null ? data.free_speaking_score_avg / 100 : null)}`}>
              {data.free_speaking_score_avg != null ? `${data.free_speaking_score_avg.toFixed(0)}/100` : '—'}
            </span>
            <span className="text-[var(--muted)]">({data.free_speaking_attempts} lần)</span>
          </div>
        )}
        {(data.conversation_attempts ?? 0) > 0 && (
          <div className="flex items-baseline gap-1 text-[11px]">
            <span className="text-[var(--muted)]">Hội thoại</span>
            <span className={`font-bold tabular-nums ${scoreColor(data.conversation_score_avg != null ? data.conversation_score_avg / 100 : null)}`}>
              {data.conversation_score_avg != null ? `${data.conversation_score_avg.toFixed(0)}/100` : '—'}
            </span>
            <span className="text-[var(--muted)]">({data.conversation_attempts} lần)</span>
          </div>
        )}
      </div>

      {data.session_metrics && (data.session_metrics.cups != null || data.session_metrics.audio_turns != null || data.session_metrics.avg_reaction_ms != null) && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 border-t border-[var(--border)] pt-1.5 text-[10px] text-[var(--muted)]">
          {data.session_metrics.cups != null && (
            <span>Cup: <strong className="text-[var(--ink)] tabular-nums">{data.session_metrics.cups}</strong></span>
          )}
          {data.session_metrics.audio_turns != null && (
            <span>Lượt nói: <strong className="text-[var(--ink)] tabular-nums">{data.session_metrics.audio_turns}</strong></span>
          )}
          {formatReactionMs(data.session_metrics.avg_reaction_ms ?? undefined) && (
            <span>TB phản xạ: <strong className="text-[var(--ink)]">{formatReactionMs(data.session_metrics.avg_reaction_ms ?? undefined)}</strong></span>
          )}
          {data.session_metrics.session_status && (
            <span className="rounded bg-teal-50 px-1 py-0.5 text-[9px] font-semibold text-teal-800">{data.session_metrics.session_status}</span>
          )}
        </div>
      )}

      {/* Câu nói sai */}
      {data.worst_speaking_items.length > 0 && (
        <div className="space-y-1.5 border-t border-[var(--border)] pt-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Câu nói cần cải thiện</p>
          {data.worst_speaking_items.map((w, i) => {
            const isConvo = w.lms_type === 'conversation'
            const isBrain = w.lms_type === 'brainstorm'
            const shell = isConvo
              ? 'border-violet-200/90 bg-gradient-to-br from-violet-50/80 to-[var(--surface)]'
              : isBrain
                ? 'border-amber-200/90 bg-gradient-to-br from-amber-50/85 to-[var(--surface)]'
                : 'border-rose-100 bg-rose-50'
            const badge = isConvo
              ? 'bg-violet-200/80 text-violet-900'
              : isBrain
                ? 'bg-amber-200/90 text-amber-950'
                : 'bg-sky-200/60 text-sky-900'
            const kind = isConvo ? 'Hội thoại' : isBrain ? 'Brainstorm (ảnh)' : 'Nói mở / warmup'
            return (
              <div key={i} className={`rounded border px-2 py-1.5 text-[11px] ${shell}`}>
                <div className="mb-0.5 flex flex-wrap items-center gap-1">
                  <span className={`rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wide ${badge}`}>
                    {kind}
                  </span>
                  {w.timestamp && <span className="ml-auto text-[10px] text-[var(--muted)]">{w.timestamp}</span>}
                </div>
                {w.question && (
                  <p className="mb-0.5 text-[var(--muted)] italic">&ldquo;{w.question}&rdquo;</p>
                )}
                {isConvo && w.expected_answer && (
                  <p className="mb-0.5 rounded border border-emerald-200/80 bg-emerald-50/90 px-1.5 py-0.5 text-[10px] text-emerald-900">
                    <span className="font-semibold">Mẫu: </span>
                    {w.expected_answer}
                  </p>
                )}
                {!isConvo && w.target_objects && w.target_objects.length > 0 && (
                  <div className="mb-0.5 flex flex-wrap gap-0.5">
                    {w.target_objects.slice(0, 5).map((obj) => (
                      <span key={obj} className="rounded border border-amber-200/90 bg-amber-50 px-1 py-0.5 text-[9px] text-amber-900">
                        {obj}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-[var(--ink)]">
                  <span className="font-medium">HS:</span> {w.user_transcript || '—'}
                </p>
                {isConvo ? (
                  <div className="mt-1 space-y-0.5 font-mono text-[10px] tabular-nums text-[var(--muted)]">
                    <div>
                      Tổng{' '}
                      <span className={`font-semibold ${scoreColor100(w.score)}`}>{w.score != null ? w.score : '—'}</span>
                      {w.grammar_score != null && (
                        <>
                          {' · '}NP <span className={`font-semibold ${scoreColor100(w.grammar_score)}`}>{w.grammar_score}</span>
                        </>
                      )}
                      {w.pronunciation_score != null && (
                        <>
                          {' · '}PA <span className={`font-semibold ${scoreColor100(w.pronunciation_score)}`}>{w.pronunciation_score}</span>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="mt-0.5 flex flex-wrap items-center gap-2">
                    {w.answer_type && (
                      <span className="rounded bg-rose-100 px-1 py-0.5 text-[10px] font-medium text-rose-700">
                        {answerTypeBadge(w.answer_type)}
                      </span>
                    )}
                    {w.score != null && (
                      <span className={`text-[10px] font-semibold tabular-nums ${scoreColor100(w.score)}`}>{w.score}/100</span>
                    )}
                  </div>
                )}
                {!isConvo && w.correct_objects && w.correct_objects.length > 0 && (
                  <p className="mt-0.5 text-[10px] text-emerald-800">
                    <span className="font-medium">Đúng:</span> {w.correct_objects.join(', ')}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function HomeworkPanel({ data }: { data: HomeworkSummary }) {
  if (!data.attempted) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2">
        <span className="mt-0.5 text-amber-500 text-[13px] leading-none">⚠</span>
        <div>
          <p className="text-[11px] font-semibold text-amber-800">Chưa nộp bài tập về nhà</p>
          <p className="text-[10px] text-amber-700 mt-0.5">Học sinh đã tham gia lớp nhưng chưa làm bài tập về nhà.</p>
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {/* Kết quả bài tập */}
      <div className="space-y-1">
        <PracticeRow label="Bài tập" result={data.bai_tap} />
        <PracticeRow label="Luyện tập" result={data.luyen_tap} />
      </div>

      {/* Kỹ năng yếu */}
      {data.weak_skills.length > 0 && (
        <div className="flex flex-wrap gap-1 border-t border-[var(--border)] pt-2">
          {data.weak_skills.map((s) => (
            <span key={s} className="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-700">
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Câu sai (text) */}
      {data.failed_text_questions.length > 0 && (
        <div className="space-y-1.5 border-t border-[var(--border)] pt-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Câu làm sai ({data.failed_text_count} câu text{data.failed_media_count > 0 ? ` + ${data.failed_media_count} có hình/âm thanh` : ''})
          </p>
          {data.failed_text_questions.map((q, i) => (
            <div key={i} className="rounded bg-amber-50 border border-amber-100 px-2 py-1.5 text-[11px]">
              {q.question_type && (
                <span className="text-[10px] font-medium text-amber-700 mr-1">[{q.question_type}]</span>
              )}
              <span className="text-[var(--ink)] italic">{q.question_text}</span>
              {q.correct_answer && (
                <p className="mt-0.5 text-emerald-700">
                  <span className="font-medium">Đáp án:</span> {q.correct_answer}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function LessonCard({ item, studentId }: { item: HistoryItem; studentId: string }) {
  const priorityScore = item.composite_priority_score
  const urgentClass = priorityScore != null && priorityScore > 0.7
    ? 'border-l-2 border-l-rose-300'
    : ''
  const activityFmt = formatActivityDateDisplay(item.last_activity_date)

  return (
    <details className={`group [&_summary::-webkit-details-marker]:hidden ${urgentClass}`}>
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2.5 text-sm hover:bg-[var(--void)]/20">
        <Link
          to={`/students/${studentId}/history/${item.lesson_id}`}
          className="min-w-0 flex-1 truncate font-medium text-[var(--ink)] hover:text-[var(--mint)] hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {item.title ?? `Bài ${item.lesson_id}`}
        </Link>

        <div className="flex shrink-0 items-center gap-1.5">
          {item.level != null && (
            <span className="rounded border border-[var(--mint)]/30 bg-[var(--mint-soft)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--mint)]">
              L{item.level}
            </span>
          )}
          {item.in_class.participated && (
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${item.in_class.is_completed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
              {item.in_class.is_completed ? '✓ Lớp' : `${item.in_class.completion_pct ?? 0}%`}
            </span>
          )}
          {item.homework.attempted ? (() => {
            const bt = item.homework.bai_tap
            const lt = item.homework.luyen_tap
            const scores = [bt?.score, lt?.score].filter((s): s is number => s != null)
            const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null
            const colorClass = avg == null ? 'bg-slate-50 text-slate-600' : avg >= 0.8 ? 'bg-emerald-50 text-emerald-700' : avg >= 0.6 ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'
            return (
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${colorClass}`}>
                BT {avg != null ? pct(avg) : '—'}
              </span>
            )
          })() : item.in_class.participated ? (
            <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
              Chưa nộp BTVN
            </span>
          ) : null}
          {activityFmt && (
            <time
              dateTime={activityFmt.dateTime}
              title={activityFmt.title}
              className="rounded border border-[var(--mint)]/25 bg-[var(--mint-soft)] px-1.5 py-0.5 text-[10px] font-medium tabular-nums tracking-tight text-[var(--muted)]"
            >
              {activityFmt.label}
            </time>
          )}
        </div>
      </summary>

      {/* Chi tiết mở rộng */}
      <div className="border-t border-[var(--border)] bg-[var(--void)]/10 px-3 pb-3 pt-2">
        <div className="grid gap-3 sm:grid-cols-2">
          {/* Trên lớp */}
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--mint)]">
              Trên lớp
            </p>
            <InClassPanel data={item.in_class} />
          </div>

          {/* Bài tập về nhà */}
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--mint)]">
              Bài tập về nhà
            </p>
            <HomeworkPanel data={item.homework} />
          </div>
        </div>

        {/* Footer: scores phụ */}
        {(item.forgetting_score != null || item.weakness_score != null) && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 border-t border-[var(--border)] pt-2 text-[10px] text-[var(--muted)]">
            {item.weakness_score != null && <span>Yếu: {item.weakness_score.toFixed(2)}</span>}
            {item.composite_priority_score != null && (
              <span className="ml-auto">Ưu tiên: {item.composite_priority_score.toFixed(2)}</span>
            )}
          </div>
        )}
      </div>
    </details>
  )
}

export default function LearningHistory() {
  const { studentId } = useParams<{ studentId: string }>()
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const grouped = useMemo(
    () => (data?.items.length ? groupHistoryByMonth(data.items) : []),
    [data],
  )

  useEffect(() => {
    if (!studentId) return
    setData(null)
    setError(null)
    fetch(`/api/students/${studentId}/history`)
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [studentId])

  if (!studentId) {
    return (
      <p className="text-[var(--muted)]">Thiếu mã học sinh trong URL.</p>
    )
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-[var(--coral)]/30 bg-[#fff1f2] p-6 text-[var(--coral)] shadow-[var(--shadow-card)]">
        <p className="font-display text-lg font-semibold">Không tải được lịch sử</p>
        <p className="mt-2 text-sm text-[var(--muted)]">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-3 text-[var(--muted)]">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--mint)]" />
        Đang tải lịch sử học tập…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="animate-rise">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">Lịch sử</p>
        <h1 className="font-display mt-1 text-2xl font-semibold text-[var(--ink)] md:text-3xl">
          Lịch sử học tập
        </h1>
        <p className="mt-1 max-w-2xl text-sm leading-snug text-[var(--muted)]">
          <span className="font-semibold text-[var(--ink)]">{data.reference_date ?? '—'}</span>
          {data.student_id != null && (
            <> · HS <span className="font-semibold text-[var(--ink)]">#{data.student_id}</span></>
          )}
          {' '}· <span className="font-semibold text-[var(--ink)]">{data.count}</span> bài học.
        </p>
      </header>

      {data.items.length === 0 ? (
        <p className="text-[var(--muted)]">Chưa có mục lịch sử.</p>
      ) : (
        <div className="space-y-3">
          {grouped.map(([monthLabel, monthItems], gi) => (
            <CollapsibleModule
              key={monthLabel}
              label={monthLabel}
              count={monthItems.length}
              defaultOpen={gi === 0}
            >
              <div className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] bg-[var(--surface)]">
                {monthItems.map((item) => (
                  <LessonCard key={item.lesson_id} item={item} studentId={studentId} />
                ))}
              </div>
            </CollapsibleModule>
          ))}
        </div>
      )}
    </div>
  )
}
