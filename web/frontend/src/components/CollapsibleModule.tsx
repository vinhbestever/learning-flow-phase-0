import { useId, useState, type ReactNode } from 'react'

type Props = {
  /** Tiêu đề nhóm (unit / chủ đề) */
  label: string
  /** Số bài trong nhóm */
  count: number
  /** Mở sẵn (vd. chỉ nhóm đầu) */
  defaultOpen?: boolean
  children: ReactNode
}

/** Nhóm có thể thu gọn — giảm chiều cao trang khi nhiều unit */
export function CollapsibleModule({ label, count, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const headId = useId()

  return (
    <section
      className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm"
      aria-labelledby={headId}
    >
      <button
        type="button"
        id={headId}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-[var(--void)]/40 focus-visible:outline focus-visible:ring-2 focus-visible:ring-[var(--mint)]"
        aria-expanded={open}
      >
        <span
          className={`inline-block h-0 w-0 border-[5px] border-transparent border-l-[6px] border-l-[var(--muted)] transition-transform ${open ? 'rotate-90' : ''}`}
          aria-hidden
        />
        <span className="min-w-0 flex-1 font-display text-base font-semibold leading-tight text-[var(--ink)] md:text-lg">
          {label}
        </span>
        <span className="shrink-0 rounded-full bg-[var(--elevated)] px-2.5 py-0.5 text-xs font-medium tabular-nums text-[var(--muted)]">
          {count} bài
        </span>
      </button>
      {open && (
        <div className="border-t border-[var(--border)] bg-[var(--void)]/30 px-2 pb-2 pt-1 md:px-3">
          {children}
        </div>
      )}
    </section>
  )
}
