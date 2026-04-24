import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { HomeworkQuestionFullDetail, type HomeworkQuestionFull } from '../components/HomeworkQuestionFullDetail'
import { InlineAudioPlayer } from '../components/InlineAudioPlayer'

// ── Types ──────────────────────────────────────────────────────────────── //

interface PhoneScore {
  phone?: string | null
  phoneIpa?: string | null
  qualityScore?: number | null
}

interface WordScore {
  word?: string | null
  qualityScore?: number | null
  phoneScoreList?: PhoneScore[] | null
}

interface PronunciationDetail {
  matched_transcripts_ipa?: string | null
  word_score_list?: WordScore[] | null
}

interface PronunciationDrill {
  expected_transcript: string
  question_prompt: string | null
  user_transcript: string | null
  pronunciation_score: number | null
  overall_score?: number | null
  audio_url?: string | null
  reaction_time_ms?: number | null
  pronunciation_detail?: PronunciationDetail | null
}

interface FreeSpeakingQuestion {
  question: string
  question_type: string | null
  expected_transcript: string | null
  target_objects: string[] | null
  user_transcript: string | null
  score: number | null
  audio_url?: string | null
  reaction_time_ms?: number | null
}

interface ConversationQuestion {
  question: string | null
  expected_transcript: string | null
  question_type: string | null
  user_transcript: string | null
  score: number | null
  grammar_score: number | null
  pronunciation_score: number | null
  audio_url?: string | null
  reaction_time_ms?: number | null
}

interface SessionMetrics {
  cups?: number | null
  audio_turns?: number | null
  avg_reaction_ms?: number | null
  fastest_reaction_ms?: number | null
  total_duration_ms?: number | null
  session_status?: string | null
}

interface QuestionRow extends HomeworkQuestionFull {
  is_failed: boolean
}

interface PracticeBlock {
  practice_id: number | null
  score: number | null
  correct: number | null
  total: number | null
  submitted_date: string | null
  questions_source?: string | null
  has_lms_attempt?: boolean
  lms_num_question?: number | null
  completed_lesson?: number | null
  questions: QuestionRow[]
}

interface InClass {
  pronunciation_drills: PronunciationDrill[]
  /** Warmup / nói mở (additionalData.warmup) — không gồm brainstorm ảnh→từ */
  free_speaking_questions: FreeSpeakingQuestion[]
  /** Brainstorm: nhìn ảnh, nói từ mục tiêu (export mới) */
  brainstorm_questions?: FreeSpeakingQuestion[]
  /** Có thể thiếu nếu dữ liệu export cũ */
  conversation_questions?: ConversationQuestion[]
  session_metrics?: SessionMetrics | null
}

interface Homework {
  attempted: boolean
  weak_skills?: string[]
  skill_breakdown?: Record<string, { correct: number; total: number; accuracy: number | null }>
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

function scoreColorClass(score: number | null | undefined, max = 100): string {
  if (score == null) return 'text-[var(--muted)]'
  const r = score / max
  if (r >= 0.8) return 'text-emerald-600'
  if (r >= 0.6) return 'text-amber-500'
  return 'text-rose-500'
}

function scoreBg(score: number | null | undefined, max = 100): string {
  if (score == null) return 'bg-slate-200/80'
  const r = score / max
  if (r >= 0.8) return 'bg-emerald-400'
  if (r >= 0.6) return 'bg-amber-400'
  return 'bg-rose-400'
}

function ScoreMiniBar({ score, max = 100, label }: { score: number | null; max?: number; label: string }) {
  const pct = score != null ? Math.round((score / max) * 100) : 0
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-14 shrink-0 text-[10px] text-[var(--muted)]">{label}</span>
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--border)]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${scoreBg(score, max)}`}
          style={{ width: score != null ? `${pct}%` : '0%' }}
        />
      </div>
      <span className={`w-8 shrink-0 text-right text-[10px] font-semibold tabular-nums ${scoreColorClass(score, max)}`}>
        {score != null ? score : '—'}
      </span>
    </div>
  )
}

function formatReactionSec(ms: number | null | undefined): string | null {
  if (ms == null || Number.isNaN(ms)) return null
  return `${(ms / 1000).toFixed(1).replace('.', ',')}s`
}

function SessionMetricsStrip({ m }: { m: SessionMetrics }) {
  const avg = formatReactionSec(m.avg_reaction_ms ?? undefined)
  const chips: { k: string; v: string }[] = []
  if (m.cups != null) chips.push({ k: 'Cup', v: String(m.cups) })
  if (m.audio_turns != null) chips.push({ k: 'Lượt nói', v: String(m.audio_turns) })
  if (avg) chips.push({ k: 'TB phản xạ', v: avg })
  if (!chips.length) return null
  return (
    <div className="flex flex-wrap gap-3 rounded-xl border border-teal-200/80 bg-gradient-to-r from-teal-50/90 to-[var(--surface)] px-3 py-2.5 text-[11px]">
      {chips.map((c) => (
        <div key={c.k}>
          <span className="block text-[9px] font-semibold uppercase tracking-wide text-teal-800/85">{c.k}</span>
          <span className="font-display text-sm font-bold tabular-nums text-[var(--ink)]">{c.v}</span>
        </div>
      ))}
    </div>
  )
}

function PronunciationPhonemePanel({ detail }: { detail: PronunciationDetail }) {
  const words = detail.word_score_list
  if (!words?.length) return null
  return (
    <div className="mt-2 space-y-2 border-t border-dashed border-fuchsia-200/70 pt-2">
      {detail.matched_transcripts_ipa && (
        <p className="text-[10px] text-[var(--muted)]">
          IPA: <span className="font-mono text-xs text-[var(--ink)]">{detail.matched_transcripts_ipa}</span>
        </p>
      )}
      {words.map((w, wi) => (
        <div key={wi} className="rounded-lg border border-[var(--border)] bg-[var(--elevated)]/40 p-2">
          <p className="text-[11px] font-semibold text-[var(--ink)]">
            {w.word ?? '—'} <span className="font-normal text-[var(--muted)]">({w.qualityScore ?? '—'}%)</span>
          </p>
          {w.phoneScoreList && w.phoneScoreList.length > 0 && (
            <table className="mt-1 w-full text-[10px]">
              <tbody>
                {w.phoneScoreList.map((ph, pi) => (
                  <tr key={pi} className="border-t border-[var(--border)]/50">
                    <td className="py-0.5 pr-2 font-mono">{ph.phone}</td>
                    <td className="py-0.5 pr-2 font-mono text-[var(--muted)]">{ph.phoneIpa}</td>
                    <td className={`py-0.5 text-right font-semibold ${(ph.qualityScore ?? 0) >= 90 ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {ph.qualityScore != null ? `${ph.qualityScore}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────── //

function PronunciationSection({ drills }: { drills: PronunciationDrill[] }) {
  if (!drills.length) return (
    <p className="text-sm italic text-[var(--muted)]">Không có bài phát âm.</p>
  )
  return (
    <details
      className="overflow-hidden rounded-xl border border-fuchsia-200/60 bg-[var(--surface)] shadow-[inset_3px_0_0_0] shadow-fuchsia-300/50 [&>summary::-webkit-details-marker]:hidden"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
        <span className="font-display tracking-tight">Phát âm ({drills.length} câu)</span>
        <span className="text-xs font-normal text-[var(--muted)]">▾</span>
      </summary>
      <ul className="max-h-[28rem] divide-y divide-[var(--border)] overflow-y-auto border-t border-[var(--border)]">
        {drills.map((d, i) => {
          const hasPhonemes = Boolean(d.pronunciation_detail?.word_score_list?.length)
          return (
            <li key={i} className="px-4 py-2.5 text-sm">
              <details className="group [&>summary::-webkit-details-marker]:hidden">
                <summary className="flex cursor-pointer list-none items-start gap-3 text-left">
                  <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[var(--ink)]">{d.expected_transcript}</p>
                    {d.question_prompt && (
                      <p className="mt-0.5 text-xs italic text-[var(--muted)]">{d.question_prompt}</p>
                    )}
                    <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-[var(--muted)]">
                      {d.reaction_time_ms != null && (
                        <span>Phản xạ: <strong className="text-[var(--ink)]">{formatReactionSec(d.reaction_time_ms)}</strong></span>
                      )}
                      {d.pronunciation_score != null && (
                        <span className={`font-semibold tabular-nums ${scoreColorClass(d.pronunciation_score, 100)}`}>
                          PA {d.pronunciation_score}/100
                        </span>
                      )}
                      {hasPhonemes && (
                        <span className="rounded-full border border-fuchsia-200 bg-fuchsia-50 px-1.5 py-0.5 text-[9px] font-bold text-fuchsia-800">IPA</span>
                      )}
                    </div>
                    {d.user_transcript && (
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        <span className="font-medium text-[var(--ink)]">Học sinh: </span>
                        {d.user_transcript}
                      </p>
                    )}
                    {d.audio_url && (
                      <InlineAudioPlayer src={d.audio_url} isolateInSummary className="mt-2" />
                    )}
                  </div>
                </summary>
                {hasPhonemes && d.pronunciation_detail && (
                  <div className="mt-2 pl-9">
                    <PronunciationPhonemePanel detail={d.pronunciation_detail} />
                  </div>
                )}
              </details>
            </li>
          )
        })}
      </ul>
    </details>
  )
}

function BrainstormSection({ questions }: { questions: FreeSpeakingQuestion[] }) {
  if (!questions.length) return null
  return (
    <details
      className="overflow-hidden rounded-xl border border-amber-200/90 bg-gradient-to-br from-amber-50/85 via-[var(--surface)] to-[var(--surface)] shadow-[inset_3px_0_0_0] shadow-amber-300/50 [&>summary::-webkit-details-marker]:hidden"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-amber-950">
        <span className="font-display tracking-tight">Brainstorm — ảnh &amp; từ mục tiêu ({questions.length} câu)</span>
        <span className="text-xs font-normal text-amber-800/80">▾</span>
      </summary>
      <ul className="divide-y divide-amber-100 border-t border-amber-200/80">
        {questions.map((q, i) => (
          <li key={i} className="px-4 py-2.5 text-sm">
            <div className="flex items-start gap-3">
              <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-[var(--ink)]">{q.question}</p>
                {q.question_type && (
                  <span className="inline-block rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-900">
                    {q.question_type}
                  </span>
                )}
                {q.target_objects && q.target_objects.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {q.target_objects.map((obj) => (
                      <span key={obj} className="rounded border border-amber-300 bg-amber-50/90 px-1.5 py-0.5 text-[10px] font-medium text-amber-950">
                        {obj}
                      </span>
                    ))}
                  </div>
                )}
                {q.user_transcript && (
                  <p className="text-xs text-[var(--muted)]">
                    <span className="font-medium text-[var(--ink)]">Học sinh: </span>
                    {q.user_transcript}
                    {q.score != null && (
                      <span className={`ml-1.5 font-semibold tabular-nums ${scoreColorClass(q.score, 100)}`}>
                        {q.score}/100
                      </span>
                    )}
                  </p>
                )}
                {(q.reaction_time_ms != null || q.audio_url) && (
                  <div className="mt-1 space-y-1.5 text-[10px] text-[var(--muted)]">
                    {q.reaction_time_ms != null && (
                      <p>
                        Phản xạ:
                        {' '}
                        <strong className="tabular-nums text-[var(--ink)]">{formatReactionSec(q.reaction_time_ms)}</strong>
                      </p>
                    )}
                    {q.audio_url && <InlineAudioPlayer src={q.audio_url} />}
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}

function FreeSpeakingSection({ questions }: { questions: FreeSpeakingQuestion[] }) {
  if (!questions.length) return (
    <p className="text-sm italic text-[var(--muted)]">Không có lượt nói mở / warmup.</p>
  )
  return (
    <details
      className="overflow-hidden rounded-xl border border-sky-200/70 bg-[var(--surface)] shadow-[inset_3px_0_0_0] shadow-sky-300/45 [&>summary::-webkit-details-marker]:hidden"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-[var(--ink)]">
        <span className="font-display tracking-tight">Nói mở / warmup ({questions.length} câu)</span>
        <span className="text-xs font-normal text-[var(--muted)]">▾</span>
      </summary>
      <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
        {questions.map((q, i) => (
          <li key={i} className="px-4 py-2.5 text-sm">
            <div className="flex items-start gap-3">
              <span className="w-6 shrink-0 tabular-nums text-[var(--muted)]">{i + 1}.</span>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-[var(--ink)]">{q.question}</p>
                {q.question_type && (
                  <span className="inline-block rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-800">
                    {q.question_type}
                  </span>
                )}
                {q.expected_transcript && (
                  <p className="rounded-lg border border-emerald-200/80 bg-emerald-50/80 px-2 py-1 text-[11px] text-emerald-900">
                    <span className="font-semibold text-emerald-800">Gợi ý: </span>
                    {q.expected_transcript}
                  </p>
                )}
                {q.user_transcript && (
                  <p className="text-xs text-[var(--muted)]">
                    <span className="font-medium text-[var(--ink)]">Học sinh: </span>
                    {q.user_transcript}
                    {q.score != null && (
                      <span className={`ml-1.5 font-semibold tabular-nums ${scoreColorClass(q.score, 100)}`}>
                        {q.score}/100
                      </span>
                    )}
                  </p>
                )}
                {(q.reaction_time_ms != null || q.audio_url) && (
                  <div className="mt-1 space-y-1.5 text-[10px] text-[var(--muted)]">
                    {q.reaction_time_ms != null && (
                      <p>
                        Phản xạ:
                        {' '}
                        <strong className="tabular-nums text-[var(--ink)]">{formatReactionSec(q.reaction_time_ms)}</strong>
                      </p>
                    )}
                    {q.audio_url && <InlineAudioPlayer src={q.audio_url} />}
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}

function ConversationSection({ questions }: { questions: ConversationQuestion[] }) {
  if (!questions.length) return null
  return (
    <details
      className="overflow-hidden rounded-xl border border-violet-200/90 bg-gradient-to-br from-violet-50/40 via-[var(--surface)] to-[var(--surface)] shadow-[inset_3px_0_0_0] shadow-violet-400/40 [&>summary::-webkit-details-marker]:hidden"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-semibold text-violet-900">
        <span className="font-display tracking-tight">Hội thoại ({questions.length} lượt)</span>
        <span className="text-xs font-normal text-violet-700/80">▾</span>
      </summary>
      <ul className="max-h-[28rem] divide-y divide-violet-100 overflow-y-auto border-t border-violet-200/80">
        {questions.map((q, i) => {
          const failed = q.score != null && q.score < 70
          return (
            <li
              key={i}
              className={`px-4 py-3 text-sm transition-colors ${failed ? 'bg-rose-50/25' : ''}`}
            >
              <div className="space-y-1.5">
                {q.question_type && (
                  <span className="inline-block rounded border border-violet-200 bg-white/70 px-1.5 py-0.5 text-[10px] font-medium text-violet-800">
                    {q.question_type}
                  </span>
                )}
                {q.question && <p className="italic text-[var(--muted)]">&ldquo;{q.question}&rdquo;</p>}
                {q.expected_transcript && (
                  <p className="rounded-lg border border-emerald-200 bg-emerald-50/90 px-2.5 py-1 text-[11px]">
                    <span className="font-semibold text-emerald-800">Câu mẫu: </span>
                    <span className="text-emerald-900">{q.expected_transcript}</span>
                  </p>
                )}
                {q.user_transcript && (
                  <p className="text-[var(--ink)]">
                    <span className="font-medium text-[var(--muted)]">Học sinh: </span>
                    {q.user_transcript}
                  </p>
                )}
                {(q.reaction_time_ms != null || q.audio_url) && (
                  <div className="mt-1 space-y-1.5 text-[10px] text-[var(--muted)]">
                    {q.reaction_time_ms != null && (
                      <p>
                        Phản xạ:
                        {' '}
                        <strong className="tabular-nums text-[var(--ink)]">{formatReactionSec(q.reaction_time_ms)}</strong>
                      </p>
                    )}
                    {q.audio_url && <InlineAudioPlayer src={q.audio_url} />}
                  </div>
                )}
                {q.score != null && (
                  <div className="space-y-1 pt-0.5">
                    <ScoreMiniBar score={q.score} label="Tổng" />
                    {q.grammar_score != null && <ScoreMiniBar score={q.grammar_score} label="Ngữ pháp" />}
                    {q.pronunciation_score != null && <ScoreMiniBar score={q.pronunciation_score} label="Phát âm" />}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </details>
  )
}

function QuestionSection({
  label,
  block,
  homeworkAttempted,
}: {
  label: string
  block: PracticeBlock | null
  homeworkAttempted: boolean
}) {
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
      {(block.questions_source || block.practice_id != null) && (
        <p className="flex flex-wrap items-center gap-2 border-t border-[var(--border)] px-4 py-2 text-[10px] text-[var(--muted)]">
          {block.practice_id != null && (
            <span className="font-mono tabular-nums">LMS <strong className="text-[var(--ink)]">{block.practice_id}</strong></span>
          )}
          {block.questions_source && (
            <span>
              {block.questions_source === 'lms_practice_result_detail' ? 'Bài làm chi tiết' : block.questions_source === 'practice_question_bank' ? 'Ngân hàng câu' : block.questions_source}
            </span>
          )}
        </p>
      )}
      {questions.length === 0 ? (
        <p className="border-t border-[var(--border)] px-4 py-3 text-sm italic text-[var(--muted)]">Không có câu hỏi.</p>
      ) : (
        <ul className="max-h-[32rem] divide-y divide-[var(--border)] overflow-y-auto border-t border-[var(--border)]">
          {questions.map((q, i) => (
            <li key={q.question_id ?? i} className="px-3 py-3">
              <HomeworkQuestionFullDetail
                q={q}
                index={i}
                practiceId={block.practice_id}
                questionsSource={block.questions_source}
                attempted={homeworkAttempted}
              />
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
  const brainstormCount = ic.brainstorm_questions?.length ?? 0
  const speakingCount = ic.free_speaking_questions.length
  const convoCount = ic.conversation_questions?.length ?? 0
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
          {(drillCount > 0 || brainstormCount > 0 || speakingCount > 0 || convoCount > 0) && (
            <span className="ml-1.5 text-xs text-[var(--muted)]">
              {drillCount + brainstormCount + speakingCount + convoCount}
            </span>
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
        <div className="space-y-4">
          {ic.session_metrics && <SessionMetricsStrip m={ic.session_metrics} />}
          <PronunciationSection drills={ic.pronunciation_drills} />
          <BrainstormSection questions={ic.brainstorm_questions ?? []} />
          <FreeSpeakingSection questions={ic.free_speaking_questions} />
          <ConversationSection questions={ic.conversation_questions ?? []} />
        </div>
      ) : (
        <div className="space-y-4">
          <QuestionSection label="Bài tập" block={hw.bai_tap} homeworkAttempted={hw.attempted} />
          <QuestionSection label="Luyện tập" block={hw.luyen_tap} homeworkAttempted={hw.attempted} />
        </div>
      )}
    </div>
  )
}
