/** Parse seconds, "90", "1:30", or "1:02:30" → seconds or null */
export function parseTimeInput(value) {
  if (value === null || value === undefined) return null
  const s = String(value).trim()
  if (!s) return null

  if (/^\d+(\.\d+)?$/.test(s)) {
    return parseFloat(s)
  }

  const parts = s.split(':').map((p) => parseFloat(p))
  if (parts.some((n) => Number.isNaN(n))) return null

  if (parts.length === 2) return parts[0] * 60 + parts[1]
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  return null
}

export function formatTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return ''
  const s = Math.floor(seconds)
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  const remS = s % 60
  const remM = m % 60
  if (h > 0) {
    return `${h}:${String(remM).padStart(2, '0')}:${String(remS).padStart(2, '0')}`
  }
  return `${m}:${String(remS).padStart(2, '0')}`
}
