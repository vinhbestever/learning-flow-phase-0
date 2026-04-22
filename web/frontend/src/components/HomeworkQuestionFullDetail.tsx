import { formatStudentAnswerDisplay } from '../lib/formatStudentAnswer'
import { hasLmsQuestionSubmission, lmsQuestionOutcome } from '../lib/lmsQuestionAttempt'
import { HomeworkQuestionRich, type ChoicePreview } from './HomeworkQuestionRich'

/** Homework question as returned by GET /api/students/.../lessons/:id */
export interface HomeworkQuestionFull {
  question_id: number | null
  question_folder: string | null
  question_type: string | null
  question_text: string | null
  comment_plain?: string | null
  requires_media: boolean
  correct_answer: string | null
  stem_media_urls?: string[]
  comment_media_urls?: string[]
  choice_previews?: ChoicePreview[]
  is_correct?: number | null
  detail_result_id?: number | null
  /** When merged from lesson API worst-question list */
  is_failed?: boolean
  student_answer?: unknown
  /** bai_tap | luyen_tap from export */
  homework_section?: string | null
  practice_id?: number | null
  questions_source?: string | null
}

function SourceBadge({ source }: { source?: string | null }) {
  if (!source || source === 'none') return null
  const label =
    source === 'lms_practice_result_detail'
      ? 'Bài làm LMS'
      : source === 'practice_question_bank'
        ? 'Ngân hàng câu'
        : source
  const cls =
    source === 'lms_practice_result_detail'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
      : 'border-amber-200 bg-amber-50 text-amber-900'
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${cls}`}>
      {label}
    </span>
  )
}

export function HomeworkQuestionFullDetail({
  q,
  index,
  practiceId,
  questionsSource,
  attempted = true,
  embedded = false,
  /** When parent already shows this type (e.g. homework result meta row), hide duplicate chip */
  typeShownAbove,
}: {
  q: HomeworkQuestionFull
  index: number
  practiceId?: number | null
  questionsSource?: string | null
  attempted?: boolean
  /** Lighter chrome when nested inside expandable rows */
  embedded?: boolean
  typeShownAbove?: string | null
}) {
  const qForAttempt = {
    ...q,
    questions_source: q.questions_source ?? questionsSource ?? null,
  }
  const stemLine = (q.question_text && q.question_text.trim()) || (q.requires_media ? 'Nội dung chủ yếu bằng hình / âm thanh' : '')
  const studentStr = formatStudentAnswerDisplay(q.student_answer)
  const hasSubmission = hasLmsQuestionSubmission(qForAttempt)
  const attemptState = lmsQuestionOutcome(qForAttempt)
  const outcomeLine =
    attemptState === 'correct'
      ? 'Đúng'
      : attemptState === 'incorrect'
        ? q.is_correct === 0
          ? 'Sai'
          : q.is_failed
            ? 'Sai (theo hồ sơ yếu)'
            : 'Sai'
        : null

  const shell = embedded
    ? 'space-y-2.5 border-0 bg-transparent p-0 shadow-none'
    : 'homework-specimen space-y-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[0_14px_40px_-28px_rgba(26,35,51,0.18)]'

  return (
    <article
      className={shell}
      style={
        embedded
          ? undefined
          : { animation: 'specimen-in 0.45s ease-out both', animationDelay: `${Math.min(index, 14) * 0.04}s` }
      }
    >
      <div className="flex flex-wrap items-center gap-1.5 border-b border-[var(--border)]/70 pb-2">
        <span className="rounded bg-[var(--ink)] px-1.5 py-0.5 font-mono text-[10px] font-bold tabular-nums text-white">
          #{q.question_id ?? index + 1}
        </span>
        {q.question_folder && (
          <span className="max-w-[min(100%,14rem)] truncate text-[10px] font-medium text-[var(--muted)]" title={q.question_folder}>
            {q.question_folder}
          </span>
        )}
        {practiceId != null && (
          <span className="font-mono text-[9px] tabular-nums text-[var(--muted-2)]">practice {practiceId}</span>
        )}
        <SourceBadge source={questionsSource} />
        {q.homework_section && (
          <span className="rounded border border-[var(--border)] bg-[var(--elevated)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--ink)]">
            {q.homework_section === 'bai_tap' ? 'Bài tập' : q.homework_section === 'luyen_tap' ? 'Luyện tập' : q.homework_section}
          </span>
        )}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-1">
          {attempted && attemptState === 'correct' && (
            <span className="rounded border border-emerald-300 bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-900">
              Đã làm · đúng
            </span>
          )}
          {attempted && attemptState === 'incorrect' && (
            <span className="rounded border border-rose-300 bg-rose-50 px-1.5 py-0.5 text-[9px] font-bold text-rose-900">
              Đã làm · sai
            </span>
          )}
          {attempted && attemptState === 'not_submitted' && (
            <span className="rounded border border-dashed border-amber-400 bg-amber-50/90 px-1.5 py-0.5 text-[9px] font-bold text-amber-950">
              Chưa làm trên LMS
            </span>
          )}
          {q.detail_result_id != null && (
            <span className="font-mono text-[9px] text-[var(--muted-2)]">result {q.detail_result_id}</span>
          )}
        </div>
      </div>

      {q.question_type && q.question_type !== typeShownAbove && (
        <span className="inline-block rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-semibold text-sky-900">
          {q.question_type}
        </span>
      )}

      {stemLine && (
        <p className="text-[13px] font-medium leading-relaxed text-[var(--ink)] md:text-sm">{stemLine}</p>
      )}

      {q.comment_plain && (
        <div className="rounded-lg border border-dashed border-[var(--amber)]/35 bg-[var(--amber-soft)]/40 px-2.5 py-2">
          <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[var(--amber)]">Gợi ý / hướng dẫn</p>
          <p className="mt-1 text-[11px] leading-snug text-[var(--ink)]">{q.comment_plain}</p>
        </div>
      )}

      <HomeworkQuestionRich
        stemMediaUrls={q.stem_media_urls}
        commentMediaUrls={q.comment_media_urls}
        choicePreviews={q.choice_previews}
      />

      <div className="grid gap-2 border-t border-[var(--border)]/60 pt-2 sm:grid-cols-2">
        <div className="rounded-lg border border-emerald-200/60 bg-emerald-50/35 px-2.5 py-2">
          <p className="text-[9px] font-semibold uppercase tracking-wide text-emerald-800">Đáp án đúng</p>
          <p className="mt-1 text-[12px] leading-snug text-emerald-950">
            {q.correct_answer && q.correct_answer.trim() ? q.correct_answer : '— (có thể chỉ là ảnh / âm thanh)'}
          </p>
        </div>
        {!attempted ? (
          <p className="rounded-lg border border-dashed border-[var(--border)] bg-[var(--elevated)]/50 px-2.5 py-2 text-[11px] text-[var(--muted)]">
            Câu trong ngân hàng — chưa có bài làm LMS để hiển thị phần nộp bài.
          </p>
        ) : !hasSubmission ? (
          <div className="rounded-lg border border-dashed border-amber-300/90 bg-amber-50/55 px-2.5 py-2">
            <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-900">Học sinh chưa làm câu này</p>
            <p className="mt-1 text-[11px] leading-snug text-amber-950/95">
              Không có dòng bài làm LMS cho mã câu này (thường là đề lấy từ ngân hàng hoặc câu chưa tới trong bài nộp).
            </p>
          </div>
        ) : (
          <div
            className={`rounded-lg border px-2.5 py-2 ${
              attemptState === 'correct'
                ? 'border-emerald-200/85 bg-emerald-50/45'
                : attemptState === 'incorrect'
                  ? 'border-rose-200/80 bg-rose-50/50'
                  : 'border-[var(--border)] bg-[var(--void)]/50'
            }`}
          >
            <p
              className={`text-[9px] font-semibold uppercase tracking-wide ${
                attemptState === 'correct' ? 'text-emerald-900' : attemptState === 'incorrect' ? 'text-rose-900' : 'text-[var(--muted)]'
              }`}
            >
              Bài làm học sinh
            </p>
            <p
              className={`mt-1 text-[12px] leading-snug ${
                attemptState === 'incorrect' ? 'text-rose-900' : attemptState === 'correct' ? 'text-emerald-950' : 'text-[var(--ink)]'
              }`}
            >
              {studentStr || '—'}
            </p>
            {outcomeLine && (
              <p
                className={`mt-1 text-[10px] font-semibold ${
                  attemptState === 'correct'
                    ? 'text-emerald-800'
                    : attemptState === 'incorrect'
                      ? 'text-rose-800'
                      : 'text-[var(--muted)]'
                }`}
              >
                Kết quả LMS: {outcomeLine}
              </p>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
