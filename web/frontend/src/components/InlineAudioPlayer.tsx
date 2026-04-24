/**
 * Inline student recording playback — compact “broadcast chip” aligned with
 * the warm classroom palette (mint / amber / ink), no new-tab-only affordance.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function InlineAudioPlayer({
  src,
  className = '',
  isolateInSummary = false,
}: {
  src: string
  className?: string
  /** Use inside `<summary>` so play does not toggle the disclosure. */
  isolateInSummary?: boolean
}) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [current, setCurrent] = useState(0)

  const stopBubble = useCallback(
    (e: React.MouseEvent | React.PointerEvent) => {
      if (isolateInSummary) e.stopPropagation()
    },
    [isolateInSummary],
  )

  const toggle = useCallback(() => {
    const el = audioRef.current
    if (!el) return
    if (playing) el.pause()
    else void el.play().catch(() => {})
  }, [playing])

  useEffect(() => {
    const el = audioRef.current
    if (!el) return
    const onLoaded = () => setDuration(Number.isFinite(el.duration) ? el.duration : 0)
    const onTime = () => setCurrent(el.currentTime)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    el.addEventListener('loadedmetadata', onLoaded)
    el.addEventListener('durationchange', onLoaded)
    el.addEventListener('timeupdate', onTime)
    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onPause)
    return () => {
      el.removeEventListener('loadedmetadata', onLoaded)
      el.removeEventListener('durationchange', onLoaded)
      el.removeEventListener('timeupdate', onTime)
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onPause)
    }
  }, [src])

  const pct = duration > 0 ? Math.min(100, (current / duration) * 100) : 0

  return (
    <div
      role="group"
      aria-label="Ghi âm học sinh"
      className={`inline-flex min-w-0 max-w-[min(100%,22rem)] items-center gap-2 rounded-xl border border-[var(--border)] bg-gradient-to-r from-[var(--amber-soft)]/90 via-[var(--surface)] to-[var(--mint-soft)]/70 px-2 py-1 shadow-[0_4px_16px_-8px_rgba(26,35,51,0.14),inset_0_1px_0_rgba(255,255,255,0.75)] ${className}`}
      onClick={stopBubble}
      onPointerDown={stopBubble}
    >
      <audio ref={audioRef} src={src} preload="metadata" />

      <button
        type="button"
        onClick={toggle}
        aria-label={playing ? 'Tạm dừng' : 'Phát ghi âm'}
        className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-white shadow-md ring-2 transition hover:ring-[var(--mint)]/50 hover:brightness-110 active:scale-[0.96] ${playing ? 'ring-[var(--mint)]/50' : 'ring-transparent'}`}
      >
        {playing ? (
          <span className="flex gap-0.5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="inline-block h-3 w-0.5 origin-bottom rounded-full bg-[var(--mint-soft)]"
                style={{
                  animation: 'bar-bounce 0.5s ease-in-out infinite',
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </span>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden className="ml-0.5">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      <div className="min-w-0 flex-1">
        <div
          className="h-1 overflow-hidden rounded-full bg-[var(--elevated-2)]/80"
          aria-hidden
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-[var(--amber)] to-[var(--mint)] transition-[width] duration-150 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-0.5 font-mono text-[9px] tabular-nums tracking-tight text-[var(--muted)]">
          {formatTime(current)}
          {' '}
          <span className="text-[var(--muted-2)]">/</span>
          {' '}
          {formatTime(duration)}
        </p>
      </div>

      <a
        href={src}
        target="_blank"
        rel="noopener noreferrer"
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)]/90 text-[var(--muted)] transition hover:border-[var(--mint)]/40 hover:text-[var(--mint)]"
        aria-label="Mở file trong tab mới"
        title="Mở trong tab mới"
        onClick={stopBubble}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </a>
    </div>
  )
}
