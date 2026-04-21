import { NavLink, Route, Routes } from 'react-router-dom'
import GenerateHomework from './pages/GenerateHomework'
import HomeworkResult from './pages/HomeworkResult'
import LearningHistory from './pages/LearningHistory'
import LessonList from './pages/LessonList'
import StudentProfile from './pages/StudentProfile'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded-full px-4 py-2 text-sm font-semibold tracking-wide transition-all duration-200',
    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mint)]',
    isActive
      ? 'bg-[var(--nav-active)] text-[var(--ink)] shadow-[0_0_0_1px_var(--nav-active-ring)]'
      : 'text-[var(--muted)] hover:bg-[var(--faint)] hover:text-[var(--ink)]',
  ].join(' ')

export default function App() {
  return (
    <div className="bg-lab min-h-dvh">
      <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--header-bg)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div className="flex items-center gap-4">
            <div
              className="relative h-11 w-11 shrink-0 rotate-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-float)]"
              aria-hidden
            >
              <span className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[var(--mint)]/20 to-transparent" />
              <span className="font-display absolute inset-0 flex items-center justify-center text-lg font-semibold text-[var(--mint)]">
                P0
              </span>
            </div>
            <div>
              <p className="font-display text-lg font-semibold leading-tight text-[var(--ink)] md:text-xl">
                Phase 0
              </p>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                Learning flow
              </p>
            </div>
          </div>

          <nav
            className="flex flex-wrap gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_1px_2px_rgba(26,35,51,0.04)]"
            aria-label="Điều hướng chính"
          >
            <NavLink to="/" end className={linkClass}>
              Học sinh
            </NavLink>
            <NavLink to="/lessons" className={linkClass}>
              Bài học
            </NavLink>
            <NavLink to="/history" className={linkClass}>
              Lịch sử
            </NavLink>
            <NavLink to="/generate" className={linkClass}>
              Tạo bài tập
            </NavLink>
            <NavLink to="/homework" className={linkClass}>
              Kết quả
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 md:px-8 md:py-14">
        <Routes>
          <Route path="/" element={<StudentProfile />} />
          <Route path="/lessons" element={<LessonList />} />
          <Route path="/history" element={<LearningHistory />} />
          <Route path="/generate" element={<GenerateHomework />} />
          <Route path="/homework" element={<HomeworkResult />} />
        </Routes>
      </main>
    </div>
  )
}
