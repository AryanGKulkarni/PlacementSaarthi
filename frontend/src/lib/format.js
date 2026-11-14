/** "Aryan G Kulkarni" -> "AK" (first + last initial) for avatars. */
export function initials(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts.at(-1)[0] : '')).toUpperCase() || '?'
}

/** "2026-02-18" (API date) -> Date at local midnight. new Date("2026-02-18") would be UTC. */
export function parseDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** "2026-02-18" -> "18 Feb 2026". */
export function formatDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(
    parseDate(iso),
  )
}

/** First word of a name, for greetings. */
export function firstName(name = '') {
  return name.trim().split(/\s+/)[0] || ''
}

/** 2516582 -> "2.4 MB", 83968 -> "82 KB". */
export function formatBytes(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${bytes} B`
}

/** API datetime ("2026-02-12T10:15:00Z") -> "12 Feb 2026". */
export function formatDateTime(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(iso))
}

const LOGO_COLORS = ['#5b47c8', '#187bb6', '#7d31a8', '#1599cf', '#0f766e', '#b45309', '#be123c', '#202020']

/** Stable background colour for a company's letter logo. */
export function logoColor(name = '') {
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return LOGO_COLORS[Math.abs(hash) % LOGO_COLORS.length]
}

/** Today as "YYYY-MM-DD" in the user's timezone (for date inputs and comparisons). */
export function localToday() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
