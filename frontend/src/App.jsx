import { useEffect } from 'react'

import { useAuth } from './auth/AuthContext.jsx'
import { Logo } from './components/ui.jsx'
import AppShell from './layout/AppShell.jsx'
import { navigate, usePath } from './lib/router.js'
import ComingSoon from './pages/ComingSoon.jsx'
import DrivesPage from './pages/DrivesPage.jsx'
import KnowledgePage from './pages/KnowledgePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import StudentDashboard from './pages/StudentDashboard.jsx'
import StudentsPage from './pages/StudentsPage.jsx'
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

  if (!user) return path === '/register' ? <RegisterPage /> : <LoginPage />

  const route = ROUTES[path]
  const Page = PAGES[path]
  return (
    <AppShell path={path}>
      {Page ? <Page /> : <ComingSoon title={route.title} icon={route.icon} />}
    </AppShell>
  )
}

// Built pages; every other route in ROUTES shows the ComingSoon placeholder.
const PAGES = {
  '/dashboard': StudentDashboard,
  '/profile': ProfilePage,
  '/students': StudentsPage,
  '/knowledge': KnowledgePage,
  '/drives': DrivesPage,
}

function FullPageLoader() {
  return (
    <div className="app-loading" role="status" aria-label="Loading">
      <Logo />
      <span className="button-spinner" aria-hidden="true" />
    </div>
  )
}
