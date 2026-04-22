import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CollapsibleModule } from '../components/CollapsibleModule'
import { groupHistoryByModule } from '../lib/lessonGroups'

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

  const grouped = useMemo(
    () => (data?.items.length ? groupHistoryByModule(data.items) : []),
    [data],
  )

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
    <div className="space-y-6">
      <header className="animate-rise">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
          Lịch sử
        </p>
        <h1 className="font-display mt-1 text-2xl font-semibold text-[var(--ink)] md:text-3xl">
          Lịch sử học tập
        </h1>
        <p className="mt-1 max-w-2xl text-sm leading-snug text-[var(--muted)]">
          <span className="font-semibold text-[var(--ink)]">{data.reference_date ?? '—'}</span>
          {data.student_id != null && (
            <>
              {' '}
              · HS <span className="font-semibold text-[var(--ink)]">#{data.student_id}</span>
            </>
          )}
          .
        </p>
      </header>

      {data.items.length === 0 ? (
        <p className="text-[var(--muted)]">Chưa có mục lịch sử.</p>
      ) : (
        <div className="space-y-3">
          {grouped.map(([moduleLabel, moduleItems], gi) => (
            <CollapsibleModule
              key={moduleLabel}
              label={moduleLabel}
              count={moduleItems.length}
              defaultOpen={gi === 0}
            >
              <div className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] bg-[var(--surface)]">
                {moduleItems.map((item) => (
                  <details
                    key={item.lesson_id}
                    className="group open:bg-[var(--void)]/25 [&_summary::-webkit-details-marker]:hidden"
                  >
                    <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2 text-sm">
                      <Link
                        to={`/lessons/${item.lesson_id}`}
                        className="min-w-0 flex-1 truncate font-medium text-[var(--ink)] hover:text-[var(--mint)] hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {item.title}
                      </Link>
                      {item.level != null && (
                        <span className="shrink-0 rounded border border-[var(--mint)]/30 bg-[var(--mint-soft)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--mint)]">
                          L{item.level}
                        </span>
                      )}
                      {item.days_since_last_practice != null && (
                        <span className="shrink-0 text-xs tabular-nums text-[var(--muted)]">
                          {item.days_since_last_practice}d
                        </span>
                      )}
                      <span className="ml-auto shrink-0 text-xs tabular-nums text-[var(--muted)]">
                        ưu tiên {item.composite_priority_score?.toFixed(2) ?? '—'}
                      </span>
                    </summary>

                    <details className="border-t border-[var(--border)] bg-[var(--void)]/15 [&>summary::-webkit-details-marker]:hidden">
                      <summary className="cursor-pointer list-none px-3 py-2 text-xs font-semibold text-[var(--mint)]">
                        Phân tích chi tiết (quên / sai bài / nói) ▾
                      </summary>
                      <div className="space-y-3 border-t border-[var(--border)] px-3 pb-3 pt-2">
                        <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-[var(--muted)]">
                          <span>Quên: {pct(item.forgetting_score)}</span>
                          <span>·</span>
                          <span>Yếu: {item.weakness_score?.toFixed(2) ?? '—'}</span>
                          {item.last_speaking_activity && (
                            <>
                              <span>·</span>
                              <span>Nói: {item.last_speaking_activity}</span>
                            </>
                          )}
                        </div>

                        {item.weak_skills.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {item.weak_skills.map((s) => (
                              <span
                                key={s}
                                className="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-900"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="grid gap-2 text-[11px] sm:grid-cols-2 sm:gap-3">
                          <div>
                            <p className="font-semibold uppercase tracking-wide text-[var(--muted)]">
                              Sai bài
                            </p>
                            <p className="mt-0.5 text-[var(--ink)]">
                              Text <strong>{item.failed_text_count}</strong> · Media{' '}
                              <strong>{item.failed_media_questions_count}</strong>
                            </p>
                            {item.failed_preview.map((fp, j) => (
                              <p key={j} className="mt-1 line-clamp-3 italic text-[var(--muted)]">
                                {fp.question_type && `${fp.question_type}: `}
                                {fp.snippet}
                              </p>
                            ))}
                          </div>
                          <div>
                            <p className="font-semibold uppercase tracking-wide text-[var(--muted)]">
                              Nói (mẫu)
                            </p>
                            {item.speaking_preview.length === 0 ? (
                              <p className="mt-0.5 text-[var(--muted)]">—</p>
                            ) : (
                              item.speaking_preview.map((sp, j) => (
                                <p key={j} className="mt-1 border-l-2 border-[var(--mint)] pl-2 text-[var(--ink)]">
                                  <span className="text-[var(--muted)]">HS:</span> {sp.user_transcript || '—'}
                                  {sp.timestamp && (
                                    <span className="ml-1 text-[var(--muted)]">({sp.timestamp})</span>
                                  )}
                                </p>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </details>
                  </details>
                ))}
              </div>
            </CollapsibleModule>
          ))}
        </div>
      )}
    </div>
  )
}
