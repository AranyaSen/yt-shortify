import { useEffect, useRef, useState } from 'react'
import { renderAllShorts } from '../lib/ffmpegClient'

export default function useClientVideoRender(jobId, status, shorts, renderMode) {
  const [renderedShorts, setRenderedShorts] = useState([])
  const [renderProgress, setRenderProgress] = useState(0)
  const [renderMessage, setRenderMessage] = useState('')
  const [renderError, setRenderError] = useState(null)
  const [renderDone, setRenderDone] = useState(false)
  const startedRef = useRef(false)
  const blobUrlsRef = useRef([])

  useEffect(() => {
    if (
      renderMode !== 'browser' ||
      status !== 'ready_to_render' ||
      !jobId ||
      !shorts?.length
    ) {
      return
    }
    if (startedRef.current) return
    startedRef.current = true

    let cancelled = false

    const run = async () => {
      setRenderError(null)
      setRenderMessage('Loading FFmpeg (multi-threaded)…')
      setRenderProgress(0.65)

      try {
        const results = await renderAllShorts(jobId, shorts, {
          onProgress: (index, total, short) => {
            if (cancelled) return
            const progress = 0.65 + (0.35 * index) / total
            setRenderProgress(progress)
            setRenderMessage(`Rendering short ${index + 1} of ${total}: ${short.title}`)
          },
          onClipDone: (rendered) => {
            if (cancelled) return
            blobUrlsRef.current.push(rendered.videoUrl)
            setRenderedShorts((prev) => [...prev, rendered])
          },
        })

        if (cancelled) return

        setRenderProgress(1)
        setRenderMessage('All shorts ready!')
        setRenderDone(true)

        await fetch(`/api/render-complete/${jobId}/`, { method: 'POST' })
      } catch (err) {
        if (cancelled) return
        setRenderError(err.message || 'Browser rendering failed')
        setRenderMessage('')
      }
    }

    run()

    return () => {
      cancelled = true
    }
  }, [jobId, status, shorts, renderMode])

  useEffect(() => {
    if (!jobId) {
      startedRef.current = false
      setRenderedShorts([])
      setRenderProgress(0)
      setRenderMessage('')
      setRenderError(null)
      setRenderDone(false)
      blobUrlsRef.current.forEach((url) => URL.revokeObjectURL(url))
      blobUrlsRef.current = []
    }
  }, [jobId])

  useEffect(() => {
    return () => {
      blobUrlsRef.current.forEach((url) => URL.revokeObjectURL(url))
      blobUrlsRef.current = []
    }
  }, [])

  return {
    renderedShorts,
    renderProgress,
    renderMessage,
    renderError,
    renderDone,
    isRendering:
      renderMode === 'browser' &&
      status === 'ready_to_render' &&
      !renderDone &&
      !renderError,
  }
}
