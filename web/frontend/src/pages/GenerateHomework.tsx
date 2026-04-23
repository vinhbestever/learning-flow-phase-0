import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

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

type HomeworkModelOption = { id: string; provider: string }

function groupModelsByProvider(models: HomeworkModelOption[]) {
  const openai: HomeworkModelOption[] = []
  const google: HomeworkModelOption[] = []
  for (const m of models) {
    if (m.provider === 'openai') openai.push(m)
    else google.push(m)
  }
  return { openai, google }
}

/** Một hàng: chọn model + bắt đầu (cùng khối) — gọn, đúng “một thao tác”. */
function PipelineModelStartBlock({
  modelOptions,
  selectedModel,
  onModelChange,
  onStart,
}: {
  modelOptions: HomeworkModelOption[]
  selectedModel: string
  onModelChange: (id: string) => void
  onStart: () => void
}) {
  const { openai, google } = useMemo(() => groupModelsByProvider(modelOptions), [modelOptions])
  const hasList = modelOptions.length > 0

  return (
    <div className="max-w-xl space-y-1.5">
      {/*
        Grid [1fr | auto]: tránh w-full trên nút trong flex row phủ cả hàng.
        Một dòng: nhãn + select — thấp hơn, gọn hơn block label/stacked.
      */}
      <div className="animate-rise grid w-full grid-cols-1 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-card)] sm:grid-cols-[minmax(0,1fr)_auto] sm:items-stretch">
        <div className="flex min-h-[2.75rem] min-w-0 items-center gap-2.5 border-b border-[var(--border)] px-3 py-2 sm:min-h-[2.5rem] sm:border-b-0 sm:pl-3.5 sm:pr-2">
          <label
            htmlFor="hw-pipeline-model"
            className="shrink-0 text-[9px] font-bold uppercase leading-none tracking-[0.2em] text-[var(--mint)]"
          >
            Model
          </label>
          <select
            id="hw-pipeline-model"
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="min-w-0 flex-1 cursor-pointer border-0 bg-transparent py-1.5 pl-0 font-mono text-[12px] font-semibold text-[var(--ink)] focus:ring-0 focus:outline-none sm:py-2.5"
          >
            {hasList ? (
              <>
                {openai.length > 0 && (
                  <optgroup label="OpenAI">
                    {openai.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.id}
                      </option>
                    ))}
                  </optgroup>
                )}
                {google.length > 0 && (
                  <optgroup label="Google Gemini">
                    {google.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.id}
                      </option>
                    ))}
                  </optgroup>
                )}
              </>
            ) : (
              <option value={selectedModel}>
                {selectedModel} (mặc định — chưa tải danh sách)
              </option>
            )}
          </select>
        </div>

        <button
          type="button"
          onClick={onStart}
          className="group relative inline-flex w-full min-w-0 min-h-[2.75rem] items-center justify-center border-t border-[var(--border)]/35 bg-gradient-to-b from-[var(--mint)] to-[#0c635c] px-3.5 py-2.5 text-[12px] font-semibold leading-none text-[var(--on-primary)] antialiased transition hover:brightness-[1.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mint)] sm:min-h-[2.5rem] sm:w-auto sm:min-w-[10.25rem] sm:border-l sm:border-t-0 sm:px-4 sm:text-[13px]"
        >
          <span className="relative z-[1] text-center">Bắt đầu tạo bài tập</span>
          <span
            className="pointer-events-none absolute inset-0 z-0 opacity-0 transition group-hover:opacity-100"
            style={{
              background:
                'radial-gradient(ellipse 100% 90% at 50% 110%, rgba(255,255,255,0.12), transparent 50%)',
            }}
            aria-hidden
          />
        </button>
      </div>
      <p className="text-[10px] leading-snug text-[var(--muted)]">
        <code>OPENAI_API_KEY</code> / <code>GOOGLE_API_KEY</code> trên server
      </p>
    </div>
  )
}

export default function GenerateHomework() {
  const { studentId } = useParams<{ studentId: string }>()
  const [steps, setSteps] = useState<string[]>([])
  const [diagnostic, setDiagnostic] = useState('')
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [modelOptions, setModelOptions] = useState<HomeworkModelOption[]>([])
  const [selectedModel, setSelectedModel] = useState('gpt-5.4')
  const wsRef = useRef<WebSocket | null>(null)
  const diagnosticRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    return () => wsRef.current?.close()
  }, [])

  useEffect(() => {
    fetch('/api/homework-models')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('cannot load models'))))
      .then((body: { default_model?: string; models?: HomeworkModelOption[] }) => {
        if (body.default_model) setSelectedModel(body.default_model)
        if (body.models?.length) setModelOptions(body.models)
      })
      .catch(() => {
        /* keep hardcoded default */
      })
  }, [])

  useEffect(() => {
    if (diagnosticRef.current) {
      diagnosticRef.current.scrollTop = diagnosticRef.current.scrollHeight
    }
  }, [diagnostic])

  function start() {
    if (!studentId) {
      setErrorMsg('Thiếu mã học sinh trong URL')
      setStatus('error')
      return
    }
    if (!selectedModel) {
      setErrorMsg('Chọn model trước khi chạy')
      setStatus('error')
      return
    }
    setSteps([])
    setDiagnostic('')
    setErrorMsg('')
    setStatus('running')

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const q = new URLSearchParams({ model: selectedModel })
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/ws/students/${studentId}/generate?${q.toString()}`,
    )
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

  if (!studentId) {
    return (
      <p className="text-[var(--muted)]">Thiếu mã học sinh trong URL.</p>
    )
  }

  return (
    <div className="space-y-6">
      <header className="animate-rise max-w-2xl space-y-1.5">
        <p className="text-[9px] font-bold uppercase tracking-[0.3em] text-[var(--mint)]">
          Pipeline
        </p>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-[var(--ink)] sm:text-3xl">
          Tạo bài tập về nhà
        </h1>
        <p className="text-sm leading-relaxed text-[var(--muted)] sm:text-[15px] sm:leading-snug">
          AI phân tích dữ liệu, tạo 15 câu. Có thể mất vài phút.
        </p>
      </header>

      {status === 'idle' && (
        <PipelineModelStartBlock
          modelOptions={modelOptions}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          onStart={start}
        />
      )}

      {status === 'running' && (
        <div className="flex flex-wrap gap-3">
          <div className="animate-rise flex items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--elevated)] px-5 py-2.5">
            <RunningIndicator />
            <span className="text-sm font-medium text-[var(--muted)]">Đang chạy pipeline</span>
          </div>
        </div>
      )}

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
            Mở trang kết quả để xem BTVN đã tạo.
          </p>
          <button
            type="button"
            onClick={() => navigate('../homework')}
            className="mt-5 rounded-full bg-[var(--ink)] px-6 py-2.5 text-sm font-bold text-[var(--on-primary)] transition hover:opacity-90"
          >
            Xem bài tập →
          </button>
        </div>
      )}
    </div>
  )
}
