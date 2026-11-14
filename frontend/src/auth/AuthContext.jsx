import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { api, setUnauthorizedHandler } from '../api/client.js'
import { clearToken, getToken, saveToken } from '../lib/tokenStorage.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Only "loading" if there is a saved token to check against /me.
  const [loading, setLoading] = useState(() => Boolean(getToken()))

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
  }, [logout])

  // Restore the session on page load.
  useEffect(() => {
    if (!getToken()) return
    api('/auth/me')
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  // Both endpoints return {access_token, user}: store the token and start the session.
  const startSession = useCallback((data, remember) => {
    saveToken(data.access_token, remember)
    setUser(data.user)
    return data.user
  }, [])

  const login = useCallback(
    async (email, password, remember = true) => {
      const data = await api('/auth/login', {
        method: 'POST',
        body: { email, password },
        auth: false,
      })
      return startSession(data, remember)
    },
    [startSession],
  )

  /** payload: StudentRegister | FacultyRegister body (see backend schemas/auth.py). */
  const register = useCallback(
    async (payload) => {
      const data = await api('/auth/register', { method: 'POST', body: payload, auth: false })
      return startSession(data, true)
    },
    [startSession],
  )

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
