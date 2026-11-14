import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { ProgressRing, ReadinessMetrics } from '../components/Readiness.jsx'
import { Badge, Button, ErrorBanner } from '../components/ui.jsx'
import { DEPARTMENTS, LEVEL_TONE } from '../lib/constants.js'
import { initials } from '../lib/format.js'

const PAGE_SIZE = 20
const SEARCH_DELAY_MS = 300
const SKILLS_IN_ROW = 3

/**
 * Faculty: students of their own department (the backend enforces it).
 * Admin: all students, with a department filter.
 */
export default function StudentsPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'admin'
  const department = DEPARTMENTS[user.department_id]

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('') // debounced value actually sent to the API
  const [departmentId, setDepartmentId] = useState('')
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)

  const [page, setPage] = useState(null) // {items, total, limit, offset}
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const searchTimer = useRef()

  // Stable so the drawer's keydown/focus effect doesn't re-run on every list re-render.
  const closeDrawer = useCallback(() => setSelectedId(null), [])

  useEffect(() => () => clearTimeout(searchTimer.current), [])

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset })
    if (search) params.set('search', search)
    if (isAdmin && departmentId) params.set('department_id', departmentId)

    api(`/students?${params}`)
      .then((data) => {
        if (!active) return
        setPage(data)
        setError('')
      })
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [search, departmentId, offset, attempt, isAdmin])

  const onSearch = (value) => {
    setSearchInput(value)
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setLoading(true)
      setSearch(value.trim())
      setOffset(0)
    }, SEARCH_DELAY_MS)
  }

  const onDepartment = (value) => {
    setLoading(true)
    setDepartmentId(value)
    setOffset(0)
  }

  const goTo = (nextOffset) => {
    setLoading(true)
    setOffset(nextOffset)
  }

  const retry = () => {
    setLoading(true)
    setError('')
    setAttempt((n) => n + 1)
  }

  const items = page?.items ?? []
  const total = page?.total ?? 0
  const filtered = Boolean(search || departmentId)

  return (
    <div className="page students-page">
      <div className="page-intro">
        <div>
          <h2>Student overview</h2>
          <p>
            {isAdmin
              ? 'Track placement readiness across all departments.'
              : `Track placement readiness of ${department?.code ?? 'your'} students.`}
          </p>
        </div>
        {page && (
          <div className="stat-inline">
            <strong>{total}</strong>
            <span>{filtered ? 'Matching students' : 'Students'}</span>
          </div>
        )}
      </div>

      <section className="card table-card">
        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={17} />
            <input
              type="search"
              aria-label="Search students by name"
              placeholder="Search students by name..."
              value={searchInput}
              maxLength={100}
              onChange={(e) => onSearch(e.target.value)}
            />
          </div>
          <div className="toolbar-right">
            {isAdmin ? (
              <select
                className="input compact"
                aria-label="Filter by department"
                value={departmentId}
                onChange={(e) => onDepartment(e.target.value)}
              >
                <option value="">All departments</option>
                {Object.entries(DEPARTMENTS).map(([id, d]) => (
                  <option key={id} value={id}>
                    {d.code}
                  </option>
                ))}
              </select>
            ) : (
              department && <Badge tone="indigo">{department.code} only</Badge>
            )}
          </div>
        </div>

        {error && (
          <div className="table-message">
            <ErrorBanner>{error}</ErrorBanner>
            <Button variant="secondary" onClick={retry}>
              Try again
            </Button>
          </div>
        )}

        {!error && !page && (
          <div className="page-loading" role="status" aria-label="Loading students">
            <span className="button-spinner" aria-hidden="true" />
          </div>
        )}

        {!error && page && items.length === 0 && (
          <div className="empty-drives">
            <Icon name="users" size={22} />
            <strong>{filtered ? 'No students match your search' : 'No students yet'}</strong>
            <p>
              {filtered
                ? 'Try a different name or clear the filters.'
                : 'Students appear here once they register for your department.'}
            </p>
          </div>
        )}

        {!error && items.length > 0 && (
          <div className={`table-scroll ${loading ? 'is-refreshing' : ''}`} aria-busy={loading}>
            <table className="student-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Branch</th>
                  <th>Year</th>
                  <th>CGPA</th>
                  <th>Skills</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((s) => (
                  <tr key={s.user_id} className="clickable-row" onClick={() => setSelectedId(s.user_id)}>
                    <td>
                      <div className="student-name">
                        <span className="avatar small">{initials(s.full_name)}</span>
                        <span>
                          <strong>{s.full_name}</strong>
                          <small>{s.email}</small>
                        </span>
                      </div>
                    </td>
                    <td>
                      <Badge>{s.department_code}</Badge>
                    </td>
                    <td>{s.year ? `Year ${s.year}` : <span className="muted-text">—</span>}</td>
                    <td>
                      {s.cgpa !== null ? (
                        <strong>{s.cgpa.toFixed(2)}</strong>
                      ) : (
                        <span className="muted-text">Not added</span>
                      )}
                    </td>
                    <td>
                      <SkillPreview skills={s.skills} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="view-link"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedId(s.user_id)
                        }}
                      >
                        View <Icon name="chevron" size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!error && total > 0 && (
          <div className="pagination">
            <span>
              Showing {offset + 1}–{offset + items.length} of {total} students
            </span>
            <div>
              <Button
                variant="secondary"
                disabled={loading || offset === 0}
                onClick={() => goTo(Math.max(0, offset - PAGE_SIZE))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={loading || offset + items.length >= total}
                onClick={() => goTo(offset + PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>

      {selectedId && <StudentDrawer studentId={selectedId} onClose={closeDrawer} />}
    </div>
  )
}

function SkillPreview({ skills }) {
  if (!skills.length) return <span className="muted-text">None added</span>
  const shown = skills.slice(0, SKILLS_IN_ROW)
  const more = skills.length - shown.length
  return (
    <div className="skill-row" title={skills.join(', ')}>
      {shown.map((s) => (
        <span className="chip simple" key={s}>
          {s}
        </span>
      ))}
      {more > 0 && <span className="muted">+{more}</span>}
    </div>
  )
}

/** "View details": full profile + readiness from GET /students/{id}. */
function StudentDrawer({ studentId, onClose }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const closeButton = useRef(null)

  useEffect(() => {
    let active = true
    api(`/students/${studentId}`)
      .then((d) => active && setDetail(d))
      .catch((err) => active && setError(err.message))
    return () => {
      active = false
    }
  }, [studentId])

  // Escape closes; focus moves into the drawer so keyboard users land in it.
  useEffect(() => {
    closeButton.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const p = detail?.profile
  const r = detail?.readiness

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Student profile">
        <div className="drawer-head">
          <div>
            <p className="overline">STUDENT PROFILE</p>
            <h2>{p?.full_name ?? 'Loading...'}</h2>
          </div>
          <button ref={closeButton} type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        {error && <ErrorBanner>{error}</ErrorBanner>}

        {!error && !detail && (
          <div className="page-loading" role="status" aria-label="Loading student">
            <span className="button-spinner" aria-hidden="true" />
          </div>
        )}

        {detail && (
          <>
            <div className="drawer-profile">
              <span className="avatar large">{initials(p.full_name)}</span>
              <h3>{p.full_name}</h3>
              <p>
                {p.email}
                {p.roll_no && <> · {p.roll_no}</>}
              </p>
              <Badge tone={LEVEL_TONE[r.level]}>
                {r.overall} readiness · {r.level}
              </Badge>
            </div>

            <div className="drawer-section">
              <h4>Placement readiness</h4>
              <div className="drawer-readiness">
                <ProgressRing score={r.overall} size={110} />
                <ReadinessMetrics params={r.params} showDetail={false} />
              </div>
            </div>

            <div className="drawer-section">
              <h4>Academic information</h4>
              <div className="detail-grid">
                <Detail label="Branch" value={p.department_code} />
                <Detail label="Year" value={p.year ? `Year ${p.year}` : null} />
                <Detail label="Passing year" value={p.passing_year} />
                <Detail label="CGPA" value={p.cgpa !== null ? `${p.cgpa.toFixed(2)} / 10` : null} />
                <Detail label="Backlogs" value={p.active_backlogs === 0 ? 'None' : `${p.active_backlogs} active`} />
                <Detail label="10th" value={p.tenth_percent !== null ? `${p.tenth_percent}%` : null} />
                <Detail label="12th / Diploma" value={p.twelfth_percent !== null ? `${p.twelfth_percent}%` : null} />
              </div>
            </div>

            <div className="drawer-section">
              <h4>Skills</h4>
              <ChipList items={p.skills} empty="No skills added" />
            </div>

            <div className="drawer-section">
              <h4>Career interests</h4>
              <ChipList items={p.interests} empty="No interests added" />
            </div>

            <div className="drawer-section">
              <h4>Experience</h4>
              <div className="detail-grid">
                <Detail label="Internships" value={p.internships} />
                <Detail label="Projects" value={p.projects} />
                <Detail label="Certifications" value={p.certifications} />
                <Detail label="Resume" value={p.has_resume ? 'Uploaded' : null} />
              </div>
            </div>

            {p.completeness.missing_fields.length > 0 && (
              <div className="drawer-section">
                <h4>Profile {p.completeness.percent}% complete</h4>
                <p className="drawer-missing">Missing: {p.completeness.missing_fields.join(', ')}</p>
              </div>
            )}

            <div className="drawer-actions">
              <a className="btn btn-primary" href={`mailto:${p.email}`}>
                <Icon name="mail" size={17} />
                <span>Contact student</span>
              </a>
            </div>
          </>
        )}
      </aside>
    </>
  )
}

function Detail({ label, value }) {
  const empty = value === null || value === undefined || value === ''
  return (
    <div>
      <span>{label}</span>
      <strong className={empty ? 'not-added' : ''}>{empty ? 'Not added' : value}</strong>
    </div>
  )
}

function ChipList({ items, empty }) {
  if (!items.length) return <p className="muted-text">{empty}</p>
  return (
    <div className="skill-row">
      {items.map((x) => (
        <span className="chip simple" key={x}>
          {x}
        </span>
      ))}
    </div>
  )
}
