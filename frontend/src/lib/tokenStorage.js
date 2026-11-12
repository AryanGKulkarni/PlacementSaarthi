// "Remember me" -> localStorage (survives closing the browser),
// otherwise sessionStorage (cleared when the tab/browser closes).
const KEY = 'placementsaarthi.token'

function safe(fn, fallback = null) {
  try {
    return fn()
  } catch {
    return fallback // storage can be blocked (private mode, strict settings)
  }
}

export function getToken() {
  return safe(() => localStorage.getItem(KEY) ?? sessionStorage.getItem(KEY))
}

export function saveToken(token, remember) {
  clearToken()
  safe(() => (remember ? localStorage : sessionStorage).setItem(KEY, token))
}

export function clearToken() {
  safe(() => localStorage.removeItem(KEY))
  safe(() => sessionStorage.removeItem(KEY))
}
