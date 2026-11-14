import { Fragment, useEffect, useState } from 'react'

import { api } from '../api/client.js'
import Icon from '../components/Icon.jsx'
import { ProgressRing, ReadinessMetrics } from '../components/Readiness.jsx'
import { Badge, Button, ErrorBanner } from '../components/ui.jsx'
import { LEVEL_TONE } from '../lib/constants.js'
import { firstName, formatDate, logoColor } from '../lib/format.js'
import { navigate } from '../lib/router.js'

// Tips come as one sentence; the Figma card shows a bold title above it.
const TIP_TITLES = {
  profile: 'Complete your profile',
  skill_gap: 'Close a skill gap',
  eligibility_gap: 'Unlock more drives',
  deadline: 'Registration closing soon',
  general: 'Placement tip',
}

const DEADLINE_SOON_DAYS = 7

export default function StudentDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [openDrive, setOpenDrive] = useState(null) // id of the expanded drive row

  useEffect(() => {
    let active = true
    api('/dashboard/student')
      .then((d) => active && setData(d))
      .catch((err) => active && setError(err.message))
    return () => {
      active = false
    }
  }, [attempt])

  if (error) {
    return (
      <div className="page dashboard-page">
        <ErrorBanner>{error}</ErrorBanner>
        <Button
          variant="secondary"
          onClick={() => {
            setError('')
            setAttempt((n) => n + 1)
          }}
        >
          Try again
        </Button>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="page-loading" role="status" aria-label="Loading dashboard">
        <span className="button-spinner" aria-hidden="true" />
      </div>
    )
  }

  const { student, readiness, tips, eligible_drives: drives } = data

  // Students have no drives page: /drives links from tips point at the table below instead.
  const followTip = (action) => {
    if (!action) return
    if (action.startsWith('/drives')) {
      const id = action.split('/')[2]
      const row = id && drives.some((d) => d.id === id) ? `drive-${id}` : 'eligible-drives'
      if (row !== 'eligible-drives') setOpenDrive(id)
      document.getElementById(row)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else {
      navigate(action)
    }
  }

  return (
    <div className="page dashboard-page">
      <div className="page-intro">
        <div>
          <h2>
            Hi, {firstName(student.full_name)} <span aria-hidden="true">👋</span>
          </h2>
          <p>Here’s how you’re tracking for placement season.</p>
        </div>
        <Button icon="spark" onClick={() => navigate('/assistant')}>
          Ask Assistant
        </Button>
      </div>

      <div className="dashboard-grid">
        <section className="card readiness-card">
          <div className="card-title-row">
            <div>
              <p className="overline">PLACEMENT READINESS</p>
              <h3>Your readiness score</h3>
            </div>
            <button type="button" className="text-link" onClick={() => navigate('/profile')}>
              Improve <Icon name="arrow" size={15} />
            </button>
          </div>
          <div className="readiness-content">
            <div className="score-column">
              <ProgressRing score={readiness.overall} />
              <Badge tone={LEVEL_TONE[readiness.level]}>{readiness.level}</Badge>
            </div>
            <ReadinessMetrics params={readiness.params} />
          </div>
        </section>

        <section className="card tips-card">
          <div className="tip-icon">
            <Icon name="bulb" />
          </div>
          <div>
            <p className="overline">PERSONALISED FOR YOU</p>
            <h3>Tips to improve</h3>
          </div>
          <div className="tips-list">
            {tips.map((tip, i) => (
              <div key={`${tip.type}-${i}`} className={tip.action ? 'tip-clickable' : ''}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                <p>
                  <strong>{TIP_TITLES[tip.type] ?? 'Tip'}</strong>
                  <small>{tip.text}</small>
                  {tip.action && (
                    <button type="button" className="text-link tip-action" onClick={() => followTip(tip.action)}>
                      {tipActionLabel(tip.action)} <Icon name="arrow" size={13} />
                    </button>
                  )}
                </p>
              </div>
            ))}
          </div>
          <button type="button" className="text-link" onClick={() => navigate('/assistant')}>
            Get a personalised plan <Icon name="arrow" size={15} />
          </button>
        </section>
      </div>

      <section className="card drives-table-card" id="eligible-drives">
        <div className="card-title-row">
          <div>
            <h3>Eligible drives</h3>
            <p>Upcoming opportunities matched to your profile</p>
          </div>
          <Badge tone="indigo">
            {drives.length} {drives.length === 1 ? 'drive' : 'drives'}
          </Badge>
        </div>

        {drives.length === 0 ? (
          <div className="empty-drives">
            <Icon name="briefcase" size={22} />
            <strong>No eligible drives right now</strong>
            <p>
              New drives for {student.department_code} will show up here. Keeping your CGPA, skills and profile up to
              date makes sure you don’t miss one.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Company & role</th>
                  <th>Minimum CGPA</th>
                  <th>Drive date</th>
                  <th>Registration</th>
                  <th>Skill match</th>
                  <th>
                    <span className="sr-only">Details</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {drives.map((d) => (
                  <DriveRow
                    key={d.id}
                    drive={d}
                    open={openDrive === d.id}
                    onToggle={() => setOpenDrive((cur) => (cur === d.id ? null : d.id))}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function DriveRow({ drive: d, open, onToggle }) {
  const soon = d.days_to_deadline !== null && d.days_to_deadline <= DEADLINE_SOON_DAYS
  return (
    <Fragment>
      <tr id={`drive-${d.id}`} className={`drive-row ${open ? 'open' : ''}`} onClick={onToggle}>
        <td>
          <div className="company-cell">
            <span className="company-logo" style={{ background: logoColor(d.company) }}>
              {d.company.trim()[0]?.toUpperCase()}
            </span>
            <span>
              <strong>{d.company}</strong>
              <small>{d.job_role}</small>
            </span>
          </div>
        </td>
        <td>{d.min_cgpa.toFixed(2)} / 10</td>
        <td>{formatDate(d.drive_date)}</td>
        <td>
          {d.registration_deadline ? (
            <>
              <Badge tone={soon ? 'amber' : 'green'}>{deadlineText(d.days_to_deadline)}</Badge>
              <small className="reason">by {formatDate(d.registration_deadline)}</small>
            </>
          ) : (
            <Badge tone="green">Open</Badge>
          )}
        </td>
        <td>
          {d.skill_match_percent === null ? (
            <span className="muted-text">No skills listed</span>
          ) : (
            <>
              <strong className="skill-match">{d.skill_match_percent}%</strong>
              <small className="reason">
                {d.matched_skills.length} of {d.required_skills.length} skills
              </small>
            </>
          )}
        </td>
        <td>
          <button
            type="button"
            className="icon-btn"
            aria-expanded={open}
            aria-label={`${open ? 'Hide' : 'Show'} details for ${d.company}`}
            onClick={(e) => {
              e.stopPropagation()
              onToggle()
            }}
          >
            <Icon name="chevron" size={16} />
          </button>
        </td>
      </tr>
      {open && (
        <tr className="drive-details-row">
          <td colSpan={6}>
            <div className="drive-details">
              <dl>
                <div>
                  <dt>Location</dt>
                  <dd>{d.location || 'Not specified'}</dd>
                </div>
                <div>
                  <dt>Package</dt>
                  <dd>{d.package_lpa !== null ? `₹${d.package_lpa} LPA` : 'Not disclosed'}</dd>
                </div>
                <div>
                  <dt>Max backlogs</dt>
                  <dd>{d.max_backlogs}</dd>
                </div>
              </dl>
              {d.required_skills.length > 0 && (
                <div className="drive-skills">
                  <span>Skills asked for</span>
                  <div>
                    {d.matched_skills.map((s) => (
                      <span className="skill-chip have" key={s}>
                        <Icon name="check" size={11} /> {s}
                      </span>
                    ))}
                    {d.missing_skills.map((s) => (
                      <span className="skill-chip missing" key={s}>
                        {s}
                      </span>
                    ))}
                  </div>
                  {d.missing_skills.length > 0 && (
                    <button
                      type="button"
                      className="text-link"
                      onClick={() =>
                        navigate(
                          `/assistant?q=${encodeURIComponent(
                            `How should I prepare ${d.missing_skills.join(', ')} for the ${d.company} ${d.job_role} drive?`,
                          )}`,
                        )
                      }
                    >
                      Ask how to prepare the missing skills <Icon name="arrow" size={13} />
                    </button>
                  )}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  )
}

function tipActionLabel(action) {
  if (action.startsWith('/profile')) return 'Update profile'
  if (action.startsWith('/assistant')) return 'Ask the assistant'
  return 'View drive'
}

function deadlineText(days) {
  if (days === 0) return 'Closes today'
  if (days === 1) return 'Closes tomorrow'
  return `Closes in ${days} days`
}

