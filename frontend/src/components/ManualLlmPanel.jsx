import { useState } from 'react'

export default function ManualLlmPanel({
  jobId,
  llmPrompt,
  transcript,
  clipStart,
  clipEnd,
  onContinue,
}) {
  const [llmResponse, setLlmResponse] = useState('')
  const [copyDone, setCopyDone] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const rangeNote =
    clipStart != null || clipEnd != null
      ? `Processing segment: ${clipStart != null ? formatSec(clipStart) : '0:00'} → ${clipEnd != null ? formatSec(clipEnd) : 'end'}`
      : 'Processing full video'

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(llmPrompt || '')
      setCopyDone(true)
      setTimeout(() => setCopyDone(false), 2000)
    } catch {
      setError('Could not copy — select and copy manually')
    }
  }

  const handleCopyTranscript = async () => {
    try {
      await navigator.clipboard.writeText(transcript || '')
    } catch {
      setError('Could not copy transcript')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const res = await fetch(`/api/continue/${jobId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ llm_response: llmResponse.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Failed to continue')
        return
      }
      onContinue?.()
    } catch {
      setError('Could not reach the backend')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="space-y-4 rounded-xl border border-cinema-accent/40 bg-cinema-surface p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl tracking-widest text-cinema-accent">
            MANUAL LLM STEP
          </h2>
          <p className="mt-1 text-sm text-cinema-muted">
            Copy the prompt → paste into ChatGPT, Claude, or any LLM → paste the JSON
            response below.
          </p>
          <p className="mt-1 text-xs text-cinema-muted">{rangeNote}</p>
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-medium uppercase tracking-wider text-cinema-muted">
            LLM prompt (includes transcript)
          </label>
          <button
            type="button"
            onClick={handleCopyPrompt}
            className="rounded border border-cinema-border px-3 py-1 text-xs font-semibold transition hover:border-cinema-accent hover:text-cinema-accent"
          >
            {copyDone ? '✓ Copied!' : 'Copy prompt'}
          </button>
        </div>
        <textarea
          readOnly
          value={llmPrompt || ''}
          rows={12}
          className="w-full resize-y rounded-lg border border-cinema-border bg-black/40 px-3 py-2 font-mono text-xs text-cinema-muted focus:outline-none"
        />
      </div>

      {transcript && (
        <details className="group">
          <summary className="cursor-pointer text-xs font-medium uppercase tracking-wider text-cinema-muted hover:text-white">
            Transcript only (optional)
          </summary>
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={handleCopyTranscript}
              className="rounded border border-cinema-border px-3 py-1 text-xs transition hover:border-cinema-accent hover:text-cinema-accent"
            >
              Copy transcript
            </button>
          </div>
          <textarea
            readOnly
            value={transcript}
            rows={8}
            className="mt-2 w-full resize-y rounded-lg border border-cinema-border bg-black/40 px-3 py-2 font-mono text-xs text-cinema-muted"
          />
        </details>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-xs font-medium uppercase tracking-wider text-cinema-muted">
          Paste LLM JSON response
        </label>
        <textarea
          required
          value={llmResponse}
          onChange={(e) => setLlmResponse(e.target.value)}
          placeholder={'[\n  {\n    "start_time": 45.2,\n    "end_time": 98.7,\n    "title": "...",\n    "hook": "...",\n    "reason": "..."\n  }\n]'}
          rows={10}
          disabled={submitting}
          className="w-full resize-y rounded-lg border border-cinema-border bg-black/60 px-3 py-2 font-mono text-sm text-white placeholder:text-cinema-muted/60 focus:border-cinema-accent focus:outline-none focus:ring-1 focus:ring-cinema-accent disabled:opacity-50"
        />

        {error && <p className="text-sm text-cinema-accent">{error}</p>}

        <button
          type="submit"
          disabled={submitting || !llmResponse.trim()}
          className="w-full rounded-lg bg-cinema-accent px-6 py-3 font-display text-xl tracking-widest text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? 'PROCESSING SHORTS…' : 'PROCESS LLM RESPONSE'}
        </button>
      </form>
    </section>
  )
}

function formatSec(sec) {
  const s = Math.floor(sec)
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${String(rem).padStart(2, '0')}`
}
