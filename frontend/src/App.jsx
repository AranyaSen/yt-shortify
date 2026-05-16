import { useState } from 'react'
import UrlForm from './components/UrlForm'
import ProgressTracker from './components/ProgressTracker'
import ShortCard from './components/ShortCard'
import ErrorBanner from './components/ErrorBanner'
import ManualLlmPanel from './components/ManualLlmPanel'
import useJobPoller from './hooks/useJobPoller'

export default function App() {
  const [jobId, setJobId] = useState(null)
  const {
    status,
    progress,
    message,
    shorts,
    error,
    llmPrompt,
    transcript,
    clipStart,
    clipEnd,
  } = useJobPoller(jobId)

  const isActive =
    jobId &&
    status &&
    !['done', 'error'].includes(status)

  const handleJobStart = (id) => {
    setJobId(id)
  }

  const handleNewJob = () => {
    if (jobId && (status === 'done' || status === 'error' || status === 'awaiting_llm')) {
      fetch(`/api/cleanup/${jobId}/`, { method: 'DELETE' }).catch(() => {})
    }
    setJobId(null)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-cinema-border px-6 py-10 text-center">
        <h1 className="font-display text-5xl tracking-[0.2em] text-white md:text-6xl">
          ⚡ SHORTIFY
        </h1>
        <p className="mt-3 text-cinema-muted">
          Turn any YouTube video into viral shorts — free &amp; local
        </p>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-6 py-10">
        <section className="rounded-xl border border-cinema-border bg-cinema-surface p-6">
          <UrlForm onJobStart={handleJobStart} disabled={isActive} />
        </section>

        {jobId && (
          <>
            <ErrorBanner error={status === 'error' ? error : null} />

            <ProgressTracker
              status={status}
              progress={progress}
              message={message}
            />

            {status === 'awaiting_llm' && llmPrompt && (
              <ManualLlmPanel
                jobId={jobId}
                llmPrompt={llmPrompt}
                transcript={transcript}
                clipStart={clipStart}
                clipEnd={clipEnd}
              />
            )}

            {shorts.length > 0 && (
              <section className="space-y-6">
                <h2 className="font-display text-2xl tracking-widest text-white">
                  YOUR SHORTS
                </h2>
                {shorts.map((short) => (
                  <ShortCard key={short.id} jobId={jobId} short={short} />
                ))}
              </section>
            )}

            {(status === 'done' || status === 'awaiting_llm') && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleNewJob}
                  className="text-sm text-cinema-muted underline-offset-4 hover:text-cinema-accent hover:underline"
                >
                  {status === 'awaiting_llm'
                    ? 'Cancel and start over'
                    : 'Generate from another video'}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
