import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type WsMsg =
  | { type: 'step'; text: string }
  | { type: 'token'; text: string }
  | { type: 'done'; homework: unknown[]; diagnostic: string }
  | { type: 'error'; text: string }

export default function GenerateHomework() {
  const [steps, setSteps] = useState<string[]>([])
  const [diagnostic, setDiagnostic] = useState('')
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

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

  return (
    <div className="space-y-10">
      <header className="animate-rise space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--mint)]">
          Pipeline
        </p>
        <h1 className="font-display text-3xl font-semibold text-[var(--ink)] md:text-4xl">
          Tạo bài tập về nhà
        </h1>
        <p className="max-w-2xl text-[var(--muted)]">
          Chạy diagnostic GPT-4o (streaming) rồi chọn 15 câu từ pool — theo dõi tiến trình theo thời
          gian thực.
        </p>
      </header>

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
          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-full border border-[var(--border)] bg-[var(--elevated)] px-8 py-3 text-sm font-semibold text-[var(--muted)] opacity-90"
          >
            Đang chạy pipeline…
          </button>
        )}
      </div>

      {steps.length > 0 && (
        <section className="animate-rise rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-card)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
            Tiến trình
          </p>
          <ul className="mt-4 space-y-2 font-mono text-sm text-[#134e4a]">
            {steps.map((s, i) => (
              <li key={`${i}-${s.slice(0, 12)}`} className="flex gap-2">
                <span className="select-none font-sans text-[var(--amber)]" aria-hidden>
                  ▶
                </span>
                <span className="font-sans text-[var(--ink)]">{s}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {diagnostic && (
        <section className="animate-rise rounded-3xl border border-[var(--border)] bg-[var(--mint-soft)]/40 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--muted)]">
            Phân tích học sinh (stream)
          </p>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">
            {diagnostic}
          </p>
        </section>
      )}

      {status === 'error' && (
        <div className="animate-rise rounded-3xl border border-[var(--coral)]/30 bg-[#fff1f2] p-6 shadow-[var(--shadow-card)]">
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

      {status === 'done' && (
        <div className="animate-rise rounded-3xl border border-[var(--mint)]/30 bg-[var(--mint-soft)] p-6 shadow-[var(--shadow-card)]">
          <p className="font-display text-lg font-semibold text-[var(--mint)]">
            Tạo bài tập thành công
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            File đã ghi vào <code className="text-[var(--ink)]">output/</code> — mở trang kết quả để
            xem 15 câu.
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
