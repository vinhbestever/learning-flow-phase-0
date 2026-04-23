import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { parseStudentFolderId } from '../lib/studentFolderLabel'

interface StudentCard {
  /** Folder name under output/ (numeric or e.g. 2111414_newstudent). */
  student_id: string
  total_lessons: number
  completed: number
  completion_pct: number
  pronunciation_avg: number | null
  free_speaking_avg: number | null
}

async function errorMessage(r: Response): Promise<string> {
  try {
    const e = await r.json()
    if (typeof e.detail === 'string') return e.detail
  } catch { /* ignore */ }
  return r.statusText || 'Lỗi không xác định'
}

export default function StudentsList() {
  const [students, setStudents] = useState<StudentCard[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/students')
      .then((r) => (r.ok ? r.json() : errorMessage(r).then((msg) => Promise.reject(msg))))
      .then(setStudents)
      .catch((e: unknown) => setError(String(e)))
  }, [])

  return (
    <div className="bg-lab min-h-dvh flex flex-col">
      <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--header-bg)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center px-4 py-4 md:px-8">
          <div>
            <p className="font-display text-lg font-semibold leading-tight text-[var(--ink)] md:text-xl">
              Phase 0
            </p>
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
              Learning flow
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 md:px-8 md:py-14">
        <div className="space-y-10">
          <header className="animate-rise space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
              Tổng quan
            </p>
            <h1 className="font-display text-3xl font-semibold text-[var(--ink)] md:text-4xl">
              Danh sách học sinh
            </h1>
            <p className="max-w-xl text-[var(--muted)]">
              Chọn học sinh để xem hồ sơ và quản lý bài tập.
            </p>
          </header>

          {error ? (
            <div className="animate-rise rounded-2xl border border-[var(--coral)]/35 bg-[#fff1f2] p-6">
              <p className="font-display font-semibold text-[var(--coral)]">Không tải được danh sách</p>
              <p className="mt-2 text-sm text-[var(--muted)]">{error}</p>
            </div>
          ) : students === null ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((k) => (
                <div key={k} className="h-52 animate-pulse rounded-2xl bg-[var(--elevated)]/80" />
              ))}
            </div>
          ) : students.length === 0 ? (
            <div className="animate-rise rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface)] p-10 text-center">
              <p className="font-display text-lg font-semibold text-[var(--muted)]">
                Chưa có dữ liệu học sinh
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Chạy <code>preprocess.py</code> để tạo dữ liệu trước.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {students.map((s, i) => {
                const folder = parseStudentFolderId(s.student_id)
                return (
                <button
                  key={s.student_id}
                  type="button"
                  title={folder.raw}
                  onClick={() => navigate(`/students/${encodeURIComponent(s.student_id)}`)}
                  className="animate-rise group relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-left shadow-[var(--shadow-card)] transition-all duration-200 hover:border-[var(--mint)]/40 hover:shadow-[var(--shadow-float)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--mint)]"
                  style={{ animationDelay: `${i * 0.08}s` }}
                >
                  <div
                    className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[var(--mint)]/[0.06] transition-all duration-300 group-hover:bg-[var(--mint)]/[0.1]"
                    aria-hidden
                  />

                  <div className="relative mb-5 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
                        Học sinh
                      </p>
                      <div className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-1.5">
                        <p className="font-display text-2xl font-bold tabular-nums tracking-tight text-[var(--ink)]">
                          #{folder.displayId}
                          {folder.isNewStudent && folder.variant != null && (
                            <span className="ml-1 text-base font-semibold text-[var(--muted)]">
                              ·{folder.variant}
                            </span>
                          )}
                        </p>
                        {folder.isNewStudent && (
                          <span
                            className="student-new-badge inline-flex shrink-0 items-center rounded-full border border-teal-300/70 bg-gradient-to-br from-[#ecfdf5] via-[#f0fdfa] to-[#e0f2fe] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-teal-900 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset,0_2px_8px_-2px_rgba(13,148,136,0.35)] ring-1 ring-teal-500/15 transition-[transform,box-shadow] duration-200 group-hover:-translate-y-px group-hover:ring-teal-400/35"
                            title="Hồ sơ thư mục newstudent (bản nhập mới)"
                          >
                            Mới
                          </span>
                        )}
                      </div>
                      {folder.isNewStudent && (
                        <p className="mt-1 truncate text-[10px] text-[var(--muted)]" title={folder.raw}>
                          Thư mục: {folder.raw}
                        </p>
                      )}
                    </div>
                    <div
                      className="relative grid h-14 w-14 shrink-0 place-items-center rounded-full p-[2.5px]"
                      style={{
                        background: `conic-gradient(var(--mint) ${s.completion_pct * 3.6}deg, var(--elevated-2) 0deg)`,
                      }}
                    >
                      <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-[var(--surface)] text-center">
                        <span className="font-display text-xs font-bold tabular-nums text-[var(--ink)]">
                          {s.completion_pct}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="relative grid grid-cols-2 gap-2">
                    <div className="rounded-lg bg-[var(--elevated)]/60 px-2.5 py-2">
                      <p className="text-[10px] font-medium text-[var(--muted)]">Bài học</p>
                      <p className="font-display font-semibold tabular-nums text-[var(--ink)]">
                        {s.completed}
                        <span className="font-normal text-[var(--muted)]">/{s.total_lessons}</span>
                      </p>
                    </div>
                    <div className="rounded-lg bg-[var(--elevated)]/60 px-2.5 py-2">
                      <p className="text-[10px] font-medium text-[var(--muted)]">Phát âm TB</p>
                      <p className="font-display font-semibold tabular-nums text-[var(--mint)]">
                        {s.pronunciation_avg != null ? s.pronunciation_avg.toFixed(0) : '—'}
                        <span className="text-[11px] font-normal text-[var(--muted)]">/100</span>
                      </p>
                    </div>
                  </div>

                  <div className="relative mt-4 flex items-center justify-end">
                    <span className="text-xs font-semibold text-[var(--mint)] opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                      Xem hồ sơ →
                    </span>
                  </div>
                </button>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
