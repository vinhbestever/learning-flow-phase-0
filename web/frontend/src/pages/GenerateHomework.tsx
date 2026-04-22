import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type WsMsg =
  | { type: 'step'; text: string }
  | { type: 'token'; text: string }
  | { type: 'done'; homework: unknown[]; diagnostic: string }
  | { type: 'error'; text: string }

function StepItem({ text, isActive, index }: { text: string; isActive: boolean; index: number }) {
  return (
    <li
      className="flex items-start gap-3 px-4 py-2.5 animate-rise"
      style={{ animationDelay: `${Math.min(index, 10) * 0.045}s` }}
    >
      <span className="mt-[5px] shrink-0">
        {isActive ? (
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--mint)] opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--mint)]" />
          </span>
        ) : (
          <span className="block h-2 w-2 rounded-full bg-[var(--mint)]/30 ring-1 ring-[var(--mint)]/40" />
        )}
      </span>
      <span
        className={`text-[13px] leading-snug ${
          isActive ? 'font-medium text-[var(--ink)]' : 'text-[var(--muted)]'
        }`}
      >
        {text}
      </span>
    </li>
  )
}

function RunningIndicator() {
  return (
    <span className="flex items-end gap-[3px]" style={{ height: '14px' }} aria-hidden>
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className="w-[3px] rounded-full bg-[var(--mint)]"
          style={{
            height: '100%',
            transformOrigin: 'bottom',
            animation: 'bar-bounce 1.1s ease-in-out infinite',
            animationDelay: `${i * 0.16}s`,
          }}
        />
      ))}
    </span>
  )
}

export default function GenerateHomework() {
  const [steps, setSteps] = useState<string[]>([])
  const [diagnostic, setDiagnostic] = useState('')
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const diagnosticRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    return () => wsRef.current?.close()
  }, [])

  useEffect(() => {
    if (diagnosticRef.current) {
      diagnosticRef.current.scrollTop = diagnosticRef.current.scrollHeight
    }
  }, [diagnostic])

  function start() {
    setSteps([])
    setDiagnostic('')
    setErrorMsg('')
    setStatus('running')

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/api/ws/generate`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg: WsMsg = JSON.parse(e.data)
      if (msg.type === 'step') {
        setSteps((s) => [...s, msg.text])
      } else if (msg.type === 'token') {
        setDiagnostic((d) => d + msg.text)
      } else if (msg.type === 'done') {
        setStatus('done')
      } else if (msg.type === 'error') {
        setErrorMsg(msg.text)
        setStatus('error')
      }
    }

    ws.onerror = () => {
      setErrorMsg('Kết nối WebSocket thất bại')
      setStatus('error')
    }
  }

  const isRunning = status === 'running'
  const isThinking = isRunning && diagnostic === ''
  const isStreaming = isRunning && diagnostic !== ''

  return (
    <div className="space-y-8">
      <header className="animate-rise space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
          Pipeline
        </p>
        <h1 className="font-display text-3xl font-semibold text-[var(--ink)] md:text-4xl">
          Tạo bài tập về nhà
        </h1>
        <p className="max-w-2xl text-[var(--muted)]">
          AI sẽ phân tích dữ liệu học sinh và tạo ra một bộ đề gồm 15 câu hỏi. Quá trình này có thể
          mất vài phút, hãy kiên nhẫn chờ đợi!
        </p>
      </header>

      {/* Action button */}
      <div className="flex flex-wrap gap-3">
        {status === 'idle' && (
          <button
            type="button"
            onClick={start}
            className="animate-rise rounded-full bg-gradient-to-r from-[var(--mint)] to-[#0f766e] px-8 py-3 text-sm font-bold uppercase tracking-[0.12em] text-[var(--on-primary)] shadow-[var(--shadow-float)] transition hover:brightness-[1.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mint)]"
          >
            Bắt đầu tạo bài tập
          </button>
        )}
        {status === 'running' && (
          <div className="animate-rise flex items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--elevated)] px-5 py-2.5">
            <RunningIndicator />
            <span className="text-sm font-medium text-[var(--muted)]">Đang chạy pipeline</span>
          </div>
        )}
      </div>

      {/* Step log */}
      {steps.length > 0 && (
        <section className="animate-rise overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-card)]">
          <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--void)]/70 px-4 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--muted)]">
              Tiến trình
            </p>
            {isRunning && (
              <span className="flex items-center gap-1.5 text-[10px] font-semibold text-[var(--mint)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--mint)] animate-pulse" />
                Đang chạy
              </span>
            )}
          </div>
          <ul className="divide-y divide-[var(--border)]/40">
            {steps.map((s, i) => (
              <StepItem
                key={`${i}-${s.slice(0, 12)}`}
                text={s}
                isActive={i === steps.length - 1 && isRunning}
                index={i}
              />
            ))}
          </ul>
        </section>
      )}

      {/* Diagnostic streaming panel */}
      {(isRunning || diagnostic) && (
        <section className="animate-rise overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-card)]">
          <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--void)]/70 px-4 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-[var(--muted)]">
              Phân tích học sinh
            </p>
            {isRunning && (
              <span className="flex items-center gap-1.5 text-[10px] font-semibold text-[var(--mint)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--mint)] animate-pulse" />
                Stream
              </span>
            )}
          </div>

          {/* Thinking skeleton — shown while waiting for first token */}
          {isThinking && (
            <div className="space-y-3 px-4 py-5">
              {[0.72, 0.48, 0.88, 0.6, 0.76].map((w, i) => (
                <div
                  key={i}
                  className="h-3 rounded-md skeleton-shimmer"
                  style={{ width: `${w * 100}%`, animationDelay: `${i * 0.1}s` }}
                />
              ))}
            </div>
          )}

          {/* Streaming content */}
          {diagnostic && (
            <div
              ref={diagnosticRef}
              className="max-h-[min(55vh,480px)] overflow-y-auto px-4 py-4"
            >
              <p className="whitespace-pre-wrap font-mono text-[13px] leading-[1.75] text-[var(--ink)]">
                {diagnostic}
                {isStreaming && (
                  <span
                    className="ml-px inline-block w-[2px] translate-y-[1px] rounded-sm bg-[var(--mint)] align-middle animate-blink"
                    style={{ height: '1.1em' }}
                    aria-hidden
                  />
                )}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="animate-rise rounded-2xl border border-[var(--coral)]/25 bg-rose-50 p-6 shadow-[var(--shadow-card)]">
          <p className="font-medium text-[var(--coral)]">{errorMsg}</p>
          <button
            type="button"
            onClick={() => {
              wsRef.current?.close()
              setStatus('idle')
            }}
            className="mt-4 text-sm font-semibold text-[var(--amber)] underline-offset-4 hover:underline"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Done */}
      {status === 'done' && (
        <div className="animate-rise rounded-2xl border border-[var(--mint)]/30 bg-[var(--mint-soft)]/60 p-6 shadow-[var(--shadow-card)]">
          <p className="font-display text-lg font-semibold text-[var(--mint)]">
            Tạo bài tập thành công
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            File đã ghi vào <code>output/</code> — mở trang kết quả để xem 15 câu.
          </p>
          <button
            type="button"
            onClick={() => navigate('/homework')}
            className="mt-5 rounded-full bg-[var(--ink)] px-6 py-2.5 text-sm font-bold text-[var(--on-primary)] transition hover:opacity-90"
          >
            Xem bài tập →
          </button>
        </div>
      )}
    </div>
  )
}
