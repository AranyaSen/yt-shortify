const STEPS = [
  { key: 'downloading', label: 'Download' },
  { key: 'transcribing', label: 'Transcribe' },
  { key: 'analyzing', label: 'Analyze' },
  { key: 'cutting', label: 'Ready' },
]

function stepIndex(status) {
  const map = {
    queued: 0,
    downloading: 0,
    transcribing: 1,
    analyzing: 2,
    awaiting_llm: 2,
    cutting: 3,
    extracting_segments: 3,
    ready_to_render: 3,
    done: 4,
    error: -1,
  }
  return map[status] ?? 0
}

export default function ProgressTracker({ status, progress, message }) {
  if (!status || status === 'error') return null

  const current = stepIndex(status)
  const pct = Math.round((progress ?? 0) * 100)
  const analyzeLabel =
    status === 'awaiting_llm' ? 'Paste LLM' : 'Analyze'

  return (
    <div className="rounded-xl border border-cinema-border bg-cinema-surface p-6">
      <ol className="mb-6 flex justify-between gap-2">
        {STEPS.map((step, i) => {
          const label = step.key === 'analyzing' ? analyzeLabel : step.label
          const active = i === current
          const done = i < current || status === 'done'
          return (
            <li key={step.key} className="flex flex-1 flex-col items-center gap-2">
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-full border text-xs font-bold ${
                  done
                    ? 'border-cinema-accent bg-cinema-accent text-white'
                    : active
                      ? 'border-cinema-accent text-cinema-accent'
                      : 'border-cinema-border text-cinema-muted'
                }`}
              >
                {done ? '✓' : i + 1}
              </span>
              <span
                className={`text-center text-xs uppercase tracking-wide ${
                  active || done ? 'text-white' : 'text-cinema-muted'
                }`}
              >
                {label}
              </span>
            </li>
          )
        })}
      </ol>

      <div className="mb-2 h-2 overflow-hidden rounded-full bg-black">
        <div
          className="h-full rounded-full bg-cinema-accent transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-sm text-cinema-muted">{message}</p>
    </div>
  )
}
