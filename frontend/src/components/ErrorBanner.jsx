export default function ErrorBanner({ error }) {
  if (!error) return null

  const isLmStudio =
    /lm\s*stu/i.test(error) ||
    error.includes('LM Studio not running')

  const display = isLmStudio
    ? 'LM Studio not running — start the local server in LM Studio, then try again.'
    : error

  return (
    <div
      role="alert"
      className="rounded-lg border border-cinema-accent/50 bg-cinema-accent/10 px-5 py-4 text-cinema-accent"
    >
      <p className="font-semibold">Generation failed</p>
      <p className="mt-1 text-sm text-red-200/90">{display}</p>
    </div>
  )
}
