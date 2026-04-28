/**
 * Cohort Station — nhãn tối giản: một viền + chữ (accent amber tách khỏi mint).
 */
export function StationTag({
  className = '',
  title = 'Học sinh thuộc nhóm trạm (Station)',
}: {
  className?: string
  title?: string
}) {
  return (
    <span
      title={title}
      className={
        'station-tag inline-flex shrink-0 items-center rounded-sm border border-amber-600/40 ' +
        'bg-[var(--surface)] px-2 py-0.5 font-display text-[10px] font-semibold uppercase ' +
        'tracking-[0.2em] text-amber-950 transition-colors duration-200 ' +
        'hover:border-amber-600/65 hover:bg-[var(--amber-soft)]/40 ' +
        className
      }
    >
      Station
    </span>
  )
}
