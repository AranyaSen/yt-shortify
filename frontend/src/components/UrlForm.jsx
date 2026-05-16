import { useState } from 'react'
import { parseTimeInput } from '../utils/parseTime'

export default function UrlForm({ onJobStart, disabled }) {
  const [url, setUrl] = useState('')
  const [model, setModel] = useState('qwen3-8b')
  const [numShorts, setNumShorts] = useState(3)
  const [useLocalLlm, setUseLocalLlm] = useState(true)
  const [renderMode, setRenderMode] = useState('native')
  const [clipStart, setClipStart] = useState('')
  const [clipEnd, setClipEnd] = useState('')
  const [submitError, setSubmitError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitError(null)

    const startSec = parseTimeInput(clipStart)
    const endSec = parseTimeInput(clipEnd)

    if (clipStart.trim() && startSec === null) {
      setSubmitError('Invalid start time — use seconds or mm:ss (e.g. 1:30)')
      return
    }
    if (clipEnd.trim() && endSec === null) {
      setSubmitError('Invalid end time — use seconds or mm:ss (e.g. 5:00)')
      return
    }
    if (startSec != null && endSec != null && endSec <= startSec) {
      setSubmitError('End time must be after start time')
      return
    }

    setLoading(true)

    try {
      const body = {
        url: url.trim(),
        model,
        num_shorts: numShorts,
        use_local_llm: useLocalLlm,
        render_mode: renderMode,
      }
      if (startSec != null) body.clip_start = startSec
      if (endSec != null) body.clip_end = endSec

      const res = await fetch('/api/generate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await res.json()
      if (!res.ok) {
        setSubmitError(data.error || 'Failed to start job')
        return
      }

      onJobStart(data.job_id)
    } catch {
      setSubmitError('Could not reach the backend. Is Django running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="youtube-url" className="sr-only">
          YouTube URL
        </label>
        <input
          id="youtube-url"
          type="url"
          required
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={disabled || loading}
          className="w-full rounded-lg border border-cinema-border bg-cinema-surface px-4 py-4 text-lg text-white placeholder:text-cinema-muted focus:border-cinema-accent focus:outline-none focus:ring-1 focus:ring-cinema-accent disabled:opacity-50"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="clip-start"
            className="mb-1 block text-xs font-medium uppercase tracking-wider text-cinema-muted"
          >
            Process from (optional)
          </label>
          <input
            id="clip-start"
            type="text"
            placeholder="0:00 or 90"
            value={clipStart}
            onChange={(e) => setClipStart(e.target.value)}
            disabled={disabled || loading}
            className="w-full rounded-lg border border-cinema-border bg-cinema-surface px-3 py-2.5 text-white placeholder:text-cinema-muted/50 focus:border-cinema-accent focus:outline-none focus:ring-1 focus:ring-cinema-accent disabled:opacity-50"
          />
          <p className="mt-1 text-xs text-cinema-muted">Leave empty for full video</p>
        </div>
        <div>
          <label
            htmlFor="clip-end"
            className="mb-1 block text-xs font-medium uppercase tracking-wider text-cinema-muted"
          >
            Process until (optional)
          </label>
          <input
            id="clip-end"
            type="text"
            placeholder="5:00 or 300"
            value={clipEnd}
            onChange={(e) => setClipEnd(e.target.value)}
            disabled={disabled || loading}
            className="w-full rounded-lg border border-cinema-border bg-cinema-surface px-3 py-2.5 text-white placeholder:text-cinema-muted/50 focus:border-cinema-accent focus:outline-none focus:ring-1 focus:ring-cinema-accent disabled:opacity-50"
          />
        </div>
      </div>

      <fieldset className="space-y-2 rounded-lg border border-cinema-border bg-black/30 px-4 py-3">
        <legend className="text-xs font-medium uppercase tracking-wider text-cinema-muted">
          Video rendering
        </legend>
        <label className="flex cursor-pointer items-start gap-3 rounded-md px-1 py-1 transition hover:text-white">
          <input
            type="radio"
            name="render-mode"
            value="native"
            checked={renderMode === 'native'}
            onChange={() => setRenderMode('native')}
            disabled={disabled || loading}
            className="mt-1 h-4 w-4 accent-cinema-accent"
          />
          <span className="text-sm text-white">
            <span className="font-semibold">I have FFmpeg installed on the system</span>
            <span className="mt-0.5 block text-xs text-cinema-muted">
              Faster — uses FFmpeg installed on the system
            </span>
          </span>
        </label>
        <label className="flex cursor-pointer items-start gap-3 rounded-md px-1 py-1 transition hover:text-white">
          <input
            type="radio"
            name="render-mode"
            value="browser"
            checked={renderMode === 'browser'}
            onChange={() => setRenderMode('browser')}
            disabled={disabled || loading}
            className="mt-1 h-4 w-4 accent-cinema-accent"
          />
          <span className="text-sm text-white">
            <span className="font-semibold">I do not have FFmpeg installed on the system (User browser FFmpeg)</span>
            <span className="mt-0.5 block text-xs text-cinema-muted">
              Runs in your browser (may take longer to render the video than native ffmpeg)
            </span>
          </span>
        </label>
      </fieldset>

      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-cinema-border bg-black/30 px-4 py-3 transition hover:border-cinema-muted">
        <input
          type="checkbox"
          checked={useLocalLlm}
          onChange={(e) => setUseLocalLlm(e.target.checked)}
          disabled={disabled || loading}
          className="h-4 w-4 accent-cinema-accent"
        />
        <span className="text-sm text-white">
          <span className="font-semibold">Use local LLM</span>
          <span className="mt-0.5 block text-xs text-cinema-muted">
            {useLocalLlm
              ? 'LM Studio analyzes the transcript automatically'
              : 'You copy the prompt, run any LLM, then paste the JSON response'}
          </span>
        </span>
      </label>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        {useLocalLlm && (
          <div className="flex-1">
            <label
              htmlFor="model"
              className="mb-1 block text-xs font-medium uppercase tracking-wider text-cinema-muted"
            >
              LM Studio model
            </label>
            <input
              id="model"
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={disabled || loading}
              className="w-full rounded-lg border border-cinema-border bg-cinema-surface px-3 py-2.5 text-white focus:border-cinema-accent focus:outline-none focus:ring-1 focus:ring-cinema-accent disabled:opacity-50"
            />
          </div>
        )}

        <div className={useLocalLlm ? 'sm:w-48' : 'flex-1 sm:max-w-xs'}>
          <label
            htmlFor="num-shorts"
            className="mb-1 flex justify-between text-xs font-medium uppercase tracking-wider text-cinema-muted"
          >
            <span>Shorts</span>
            <span className="text-cinema-accent">{numShorts}</span>
          </label>
          <input
            id="num-shorts"
            type="range"
            min={1}
            max={10}
            value={numShorts}
            onChange={(e) => setNumShorts(Number(e.target.value))}
            disabled={disabled || loading}
            className="w-full accent-cinema-accent"
          />
        </div>
      </div>

      {submitError && (
        <p className="text-sm text-cinema-accent">{submitError}</p>
      )}

      <button
        type="submit"
        disabled={disabled || loading}
        className="w-full rounded-lg bg-cinema-accent px-6 py-4 font-display text-2xl tracking-widest text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? 'STARTING…' : 'GENERATE SHORTS'}
      </button>
    </form>
  )
}
