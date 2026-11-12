import { useState } from 'react'

import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { Badge, Logo } from '../components/ui.jsx'
import { APP_NAME, DEPARTMENTS, ROLE_LABELS } from '../lib/constants.js'
import { initials } from '../lib/format.js'
import { navigate } from '../lib/router.js'
import { NAV, ROUTES } from '../routes.js'

export default function AppShell({ path, children }) {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  const nav = NAV[user.role] ?? []
  const department = DEPARTMENTS[user.department_id]
  const roleLabel = ROLE_LABELS[user.role] ?? user.role

  const go = (to) => {
    navigate(to)
    setMobileOpen(false)
  }

  return (
    <div className="app-shell">
      {mobileOpen && <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />}

      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-head">
          <Logo />
          <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <Icon name="close" />
          </button>
        </div>

        <div className="workspace">
          <div className="college-mark">{department ? department.code.slice(0, 2) : 'PS'}</div>
          <div>
            <strong>{department ? department.code : 'All departments'}</strong>
            <span>{department ? department.name : 'Placement Cell'}</span>
          </div>
        </div>

        <p className="nav-label">Workspace</p>
        <nav>
          {nav.map((to) => {
            const route = ROUTES[to]
            return (
              <button
                key={to}
                onClick={() => go(to)}
                className={`nav-item ${path === to ? 'active' : ''}`}
                aria-current={path === to ? 'page' : undefined}
              >
                <Icon name={route.icon} />
                <span>{route.label}</span>
                {to === '/assistant' && <span className="new-pill">AI</span>}
              </button>
            )
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="side-user">
            <span className="avatar">{initials(user.full_name || user.email)}</span>
            <span>
              <strong>{user.full_name || user.email}</strong>
              <small>{roleLabel}</small>
            </span>
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <button className="menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Icon name="menu" />
          </button>
          <div>
            <p className="eyebrow-mobile">{APP_NAME}</p>
            <h1>{ROUTES[path]?.title ?? APP_NAME}</h1>
          </div>
          <div className="top-actions">
            <Badge tone={user.role === 'student' ? 'indigo' : 'neutral'}>{roleLabel}</Badge>
            <button className="logout-btn" onClick={logout}>
              <Icon name="logout" size={17} />
              <span>Log out</span>
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  )
}
