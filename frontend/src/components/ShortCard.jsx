function formatTime(seconds) {
  const s = Math.floor(seconds)
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${String(rem).padStart(2, '0')}`
}

export default function ShortCard({ jobId, short }) {
  const videoSrc = `/api/download/${jobId}/${short.id}/`
  const downloadHref = videoSrc

  return (
    <article className="overflow-hidden rounded-xl border border-cinema-border bg-cinema-surface">
      <div className="flex flex-col gap-4 p-5 lg:flex-row">
        <div className="mx-auto w-full max-w-[280px] shrink-0">
          <video
            src={videoSrc}
            controls
            preload="metadata"
            className="aspect-[9/16] w-full rounded-lg bg-black object-cover"
          />
        </div>

        <div className="flex flex-1 flex-col gap-3">
          <h3 className="font-display text-3xl leading-tight tracking-wide text-white">
            {short.title}
          </h3>
          {short.hook && (
            <p className="text-base italic text-cinema-muted">&ldquo;{short.hook}&rdquo;</p>
          )}
          {short.reason && (
            <span className="inline-block w-fit rounded-full bg-cinema-accent/20 px-3 py-1 text-xs font-medium text-cinema-accent">
              {short.reason}
            </span>
          )}
          <p className="font-mono text-sm text-cinema-muted">
            {formatTime(short.start_time)} → {formatTime(short.end_time)} (
            {Math.round(short.duration)}s)
          </p>
          <a
            href={downloadHref}
            download={`${short.id}.mp4`}
            className="mt-auto inline-flex w-fit items-center gap-2 rounded-lg border border-cinema-border px-4 py-2.5 text-sm font-semibold transition hover:border-cinema-accent hover:text-cinema-accent"
          >
            ⬇ Download MP4
          </a>
        </div>
      </div>
    </article>
  )
}
