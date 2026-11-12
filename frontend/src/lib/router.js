// Minimal history-based router (no extra dependency for now).
// Real URLs like /dashboard work on refresh: nginx falls back to index.html.

import { useSyncExternalStore } from 'react'

const EVENT = 'placementsaarthi:navigate'

function subscribe(callback) {
  window.addEventListener('popstate', callback)
  window.addEventListener(EVENT, callback)
  return () => {
    window.removeEventListener('popstate', callback)
    window.removeEventListener(EVENT, callback)
  }
}

export function usePath() {
  return useSyncExternalStore(subscribe, () => window.location.pathname)
}

export function navigate(path, { replace = false } = {}) {
  if (path === window.location.pathname) return
  window.history[replace ? 'replaceState' : 'pushState'](null, '', path)
  window.dispatchEvent(new Event(EVENT))
}
