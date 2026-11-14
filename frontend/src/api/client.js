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

/** responseType 'blob' returns the raw file (e.g. a PDF) instead of parsed JSON. */
export async function api(
  path,
  { method = 'GET', body, auth = true, headers = {}, responseType = 'json' } = {},
) {
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

  if (res.ok && responseType === 'blob') return res.blob()

  const data = res.status === 204 ? null : await res.json().catch(() => null)

  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, errorMessage(res.status, data), data?.detail)
  }
  return data
}

/**
 * Multipart upload with progress. fetch can't report upload progress, so this uses XHR.
 * onProgress(percent 0-100) is called while the file is being sent.
 */
export function uploadFile(path, formData, { method = 'POST', onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open(method, `/api${path}`)
    xhr.setRequestHeader('Accept', 'application/json')
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((100 * e.loaded) / e.total))
      }
    }
    xhr.onerror = () => reject(new ApiError(0, "Can't reach the server. Check your connection and try again."))
    xhr.onload = () => {
      let data = null
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        // non-JSON body (e.g. proxy error page)
      }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(data)
      if (xhr.status === 401 && token) onUnauthorized()
      reject(new ApiError(xhr.status, errorMessage(xhr.status, data), data?.detail))
    }
    xhr.send(formData)
  })
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
