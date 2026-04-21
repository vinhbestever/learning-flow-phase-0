import { useEffect, useState } from 'react'

interface HistoryItem {
  lesson_id: number
  title: string
  level: number | null
  days_since_last_practice: number | null
  forgetting_score: number | null
  weakness_score: number | null
  composite_priority_score: number | null
  weak_skills: string[]
  failed_text_count: number
  failed_media_questions_count: number
  failed_preview: { question_type: string | null; snippet: string }[]
  speaking_preview: {
    question: string
    user_transcript: string
    answer_type: string | null
    score: number | null
    timestamp: string | null
  }[]
  last_speaking_activity: string | null
}

interface HistoryResponse {
  student_id: number | null
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
  } catch {
    /* ignore */
  }
  return r.statusText || 'Lỗi không xác định'
}

function pct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return `${(n * 100).toFixed(0)}%`
}

export default function LearningHistory() {
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/history')
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setData)
      .catch((e: unknown) => setError(String(e)))
  }, [])

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
    <div className="space-y-12">
      <header className="animate-rise">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
          Dòng thời gian
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold text-[var(--ink)] md:text-4xl">
          Lịch sử học tập
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--muted)]">
          Các bài học đã phân tích từ dữ liệu luyện tập — ưu tiên hiển thị bài luyện gần đây trước.
          Dữ liệu theo ngày tham chiếu{' '}
          <span className="font-semibold text-[var(--ink)]">{data.reference_date ?? '—'}</span>
          {data.student_id != null && (
            <>
              , học sinh <span className="font-semibold text-[var(--ink)]">#{data.student_id}</span>
            </>
          )}
          .
        </p>
      </header>

      {data.items.length === 0 ? (
        <p className="text-[var(--muted)]">Chưa có mục lịch sử.</p>
      ) : (
        <div className="relative">
          {/* Đường timeline — lệch nhẹ editorial */}
          <div
            className="absolute bottom-0 left-[1.125rem] top-8 w-px bg-gradient-to-b from-[var(--mint)] via-[var(--border)] to-transparent md:left-5"
            aria-hidden
          />

          <ol className="space-y-8">
            {data.items.map((item, i) => (
              <li
                key={item.lesson_id}
                className="animate-rise relative flex gap-5 pl-1 md:gap-8"
                style={{ animationDelay: `${Math.min(i, 14) * 0.04}s` }}
              >
                <div className="relative z-[1] flex shrink-0 flex-col items-center">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-[var(--surface)] bg-[var(--mint-soft)] font-display text-sm font-bold text-[var(--mint)] shadow-[var(--shadow-card)] md:h-10 md:w-10">
                    {i + 1}
                  </span>
                </div>

                <article className="min-w-0 flex-1 rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-card)] md:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-display text-lg font-semibold leading-snug text-[var(--ink)] md:text-xl">
                        {item.title}
                      </h2>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        {item.level != null && (
                          <span className="rounded-full border border-[var(--mint)]/35 bg-[var(--mint-soft)] px-2.5 py-0.5 font-semibold text-[var(--mint)]">
                            Cấp {item.level}
                          </span>
                        )}
                        {item.days_since_last_practice != null && (
                          <span className="rounded-full border border-[var(--border)] bg-[var(--elevated)] px-2.5 py-0.5 text-[var(--muted)]">
                            {item.days_since_last_practice} ngày từ lần luyện gần nhất
                          </span>
                        )}
                        {item.last_speaking_activity && (
                          <span className="rounded-full border border-[var(--amber)]/30 bg-[var(--amber-soft)] px-2.5 py-0.5 tabular-nums text-[var(--amber)]">
                            Nói: {item.last_speaking_activity}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-xs leading-relaxed text-[var(--muted)]">
                      <div>
                        Ưu tiên:{' '}
                        <span className="font-semibold text-[var(--ink)]">
                          {item.composite_priority_score != null
                            ? item.composite_priority_score.toFixed(2)
                            : '—'}
                        </span>
                      </div>
                      <div className="mt-1">
                        Quên (ước lượng): {pct(item.forgetting_score)} · Điểm yếu:{' '}
                        {item.weakness_score != null ? item.weakness_score.toFixed(2) : '—'}
                      </div>
                    </div>
                  </div>

                  {item.weak_skills.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {item.weak_skills.map((s) => (
                        <span
                          key={s}
                          className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-900"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-4 grid gap-4 border-t border-[var(--border)] pt-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                        Bài tập / điền
                      </p>
                      <p className="mt-1 text-sm text-[var(--ink)]">
                        Sai (text): <strong>{item.failed_text_count}</strong> · Media:{' '}
                        <strong>{item.failed_media_questions_count}</strong>
                      </p>
                      {item.failed_preview.map((fp, j) => (
                        <p key={j} className="mt-2 line-clamp-3 text-xs italic text-[var(--muted)]">
                          {fp.question_type && <span className="not-italic">{fp.question_type}: </span>}
                          {fp.snippet}
                          {fp.snippet.length >= 140 ? '…' : ''}
                        </p>
                      ))}
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                        Nói (mẫu)
                      </p>
                      {item.speaking_preview.length === 0 ? (
                        <p className="mt-1 text-sm text-[var(--muted)]">Không có đoạn nói tiêu biểu.</p>
                      ) : (
                        item.speaking_preview.map((sp, j) => (
                          <blockquote
                            key={j}
                            className="mt-2 border-l-[3px] border-[var(--mint)] pl-3 text-sm"
                          >
                            <p className="text-[var(--ink)]">&ldquo;{sp.question}&rdquo;</p>
                            <p className="mt-1 text-[var(--muted)]">
                              HS: <span className="text-[var(--ink)]">{sp.user_transcript || '—'}</span>
                              {sp.timestamp && (
                                <span className="ml-2 tabular-nums text-xs">({sp.timestamp})</span>
                              )}
                            </p>
                          </blockquote>
                        ))
                      )}
                    </div>
                  </div>
                </article>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
