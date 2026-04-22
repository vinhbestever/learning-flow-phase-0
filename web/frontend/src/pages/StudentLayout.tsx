import { Link, NavLink, Outlet, useParams } from 'react-router-dom'

export default function StudentLayout() {
  const { studentId } = useParams<{ studentId: string }>()
  const base = `/students/${studentId}`

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'rounded-full px-4 py-2 text-sm font-semibold tracking-wide transition-all duration-200',
      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mint)]',
      isActive
        ? 'bg-[var(--nav-active)] text-[var(--ink)] shadow-[0_0_0_1px_var(--nav-active-ring)]'
        : 'text-[var(--muted)] hover:bg-[var(--faint)] hover:text-[var(--ink)]',
    ].join(' ')

  return (
    <div className="bg-lab min-h-dvh">
      <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--header-bg)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--mint)]/35 hover:text-[var(--mint)]"
            >
              ← Học sinh
            </Link>
            <div>
              <p className="font-display text-lg font-semibold leading-tight text-[var(--ink)] md:text-xl">
                Phase 0
              </p>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                #{studentId}
              </p>
            </div>
          </div>

          <nav
            className="flex flex-wrap gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_1px_2px_rgba(26,35,51,0.04)]"
            aria-label="Điều hướng học sinh"
          >
            <NavLink to={base} end className={linkClass}>Học sinh</NavLink>
            <NavLink to={`${base}/history`} className={linkClass}>Lịch sử</NavLink>
            <NavLink to={`${base}/lessons`} className={linkClass}>Bài học</NavLink>
            <NavLink to={`${base}/generate`} className={linkClass}>Tạo bài tập</NavLink>
            <NavLink to={`${base}/homework`} className={linkClass}>Kết quả</NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 md:px-8 md:py-14">
        <Outlet />
      </main>
    </div>
  )
}
