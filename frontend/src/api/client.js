// Thin fetch wrapper for the PlacementSaarthi API.
// In dev, Vite proxies /api -> localhost:8000; in Docker, nginx proxies /api -> backend.

import { getToken } from '../lib/tokenStorage.js'

export class ApiError extends Error {
  constructor(status, message, detail) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

let onUnauthorized = () => {}

/** AuthProvider registers this so an expired/invalid token logs the user out. */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

export async function api(path, { method = 'GET', body, auth = true, headers = {} } = {}) {
  const init = { method, headers: { Accept: 'application/json', ...headers } }

  if (body instanceof FormData) {
    init.body = body // browser sets the multipart boundary
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }

  const token = auth ? getToken() : null
  if (token) init.headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null)

  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, errorMessage(res.status, data), data?.detail)
  }
  return data
}

/** FastAPI errors: {"detail": "text"} from our handlers, or {"detail": [{loc, msg}, ...]} for 422. */
function errorMessage(status, data) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d.msg?.replace(/^Value error, /, '')).filter(Boolean).join('. ')
  }
  if (status >= 500) return 'Something went wrong on our side. Please try again.'
  return 'Request failed. Please try again.'
}
