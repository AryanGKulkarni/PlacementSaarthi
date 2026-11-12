import { useEffect } from 'react'

import { useAuth } from './auth/AuthContext.jsx'
import { Logo } from './components/ui.jsx'
import AppShell from './layout/AppShell.jsx'
import { navigate, usePath } from './lib/router.js'
import ComingSoon from './pages/ComingSoon.jsx'
import LoginPage from './pages/LoginPage.jsx'
import { ROUTES, canAccess, homeFor } from './routes.js'

const PUBLIC_PATHS = ['/login', '/register']

export default function App() {
  const { user, loading } = useAuth()
  const path = usePath()

  // Where this user should actually be: logged out -> /login, logged in -> a page they may see.
  let target = path
  if (!loading) {
    if (!user && !PUBLIC_PATHS.includes(path)) target = '/login'
    else if (user && !canAccess(user.role, path)) target = homeFor(user.role)
  }

  useEffect(() => {
    if (target !== path) navigate(target, { replace: true })
  }, [target, path])

  if (loading || target !== path) return <FullPageLoader />

  if (!user) {
    // Register page is next; until then it reuses the placeholder.
    return path === '/register' ? <RegisterPlaceholder /> : <LoginPage />
  }

  const route = ROUTES[path]
  return (
    <AppShell path={path}>
      <ComingSoon title={route.title} icon={route.icon} />
    </AppShell>
  )
}

function FullPageLoader() {
  return (
    <div className="app-loading" role="status" aria-label="Loading">
      <Logo />
      <span className="button-spinner" aria-hidden="true" />
    </div>
  )
}

function RegisterPlaceholder() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-head">
          <h1>Create your account</h1>
          <p>Registration is coming soon.</p>
        </div>
        <div className="auth-switch">
          Already have an account?{' '}
          <button type="button" onClick={() => navigate('/login')}>
            Log in
          </button>
        </div>
      </div>
    </div>
  )
}
