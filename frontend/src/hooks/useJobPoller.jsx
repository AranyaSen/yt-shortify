import { useEffect, useRef, useState } from 'react'

export default function useJobPoller(jobId) {
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [shorts, setShorts] = useState([])
  const [error, setError] = useState(null)
  const [llmPrompt, setLlmPrompt] = useState(null)
  const [transcript, setTranscript] = useState(null)
  const [clipStart, setClipStart] = useState(null)
  const [clipEnd, setClipEnd] = useState(null)
  const timeoutRef = useRef(null)
  const statusRef = useRef(null)

  const pollInterval = (status) => (status === 'cutting' ? 10000 : 5000)

  useEffect(() => {
    if (!jobId) return

    let active = true

    const stop = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }

    const scheduleNext = () => {
      stop()
      if (!active) return
      const status = statusRef.current
      if (status === 'done' || status === 'error') return
      timeoutRef.current = setTimeout(poll, pollInterval(status))
    }

    const poll = async () => {
      try {
        const res = await fetch(`/api/status/${jobId}/`)
        if (!res.ok) {
          scheduleNext()
          return
        }
        const data = await res.json()
        if (!active) return

        statusRef.current = data.status
        setStatus(data.status)
        setProgress(data.progress ?? 0)
        setMessage(data.message ?? '')
        setShorts(data.shorts ?? [])
        setError(data.error ?? null)
        setLlmPrompt(data.llm_prompt ?? null)
        setTranscript(data.transcript ?? null)
        setClipStart(data.clip_start ?? null)
        setClipEnd(data.clip_end ?? null)

        if (data.status === 'done' || data.status === 'error') {
          stop()
          return
        }
        scheduleNext()
      } catch {
        scheduleNext()
      }
    }

    poll()

    return () => {
      active = false
      stop()
    }
  }, [jobId])

  return {
    status,
    progress,
    message,
    shorts,
    error,
    llmPrompt,
    transcript,
    clipStart,
    clipEnd,
  }
}
