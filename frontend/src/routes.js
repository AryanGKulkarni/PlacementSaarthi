// Page metadata + which pages each role sees in the sidebar.
// Pages are built one by one; until then they render a placeholder (see App.jsx).

export const ROUTES = {
  '/dashboard': { label: 'Dashboard', title: 'Dashboard', icon: 'grid' },
  '/assistant': { label: 'Assistant', title: 'AI Assistant', icon: 'spark' },
  '/profile': { label: 'Profile', title: 'My Profile', icon: 'user' },
  '/students': { label: 'Students', title: 'Students', icon: 'users' },
  '/knowledge': { label: 'Knowledge Base', title: 'Knowledge Base', icon: 'file' },
  '/drives': { label: 'Placement Drives', title: 'Placement Drives', icon: 'briefcase' },
}

export const NAV = {
  student: ['/dashboard', '/assistant', '/profile'],
  faculty: ['/students', '/knowledge', '/drives', '/assistant'],
  admin: ['/students', '/knowledge', '/drives', '/assistant'],
}

/** First page after login (and where unknown URLs go). */
export function homeFor(role) {
  return NAV[role]?.[0] ?? '/dashboard'
}

export function canAccess(role, path) {
  return NAV[role]?.includes(path) ?? false
}
