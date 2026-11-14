import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { useToast } from '../components/Toast.jsx'
import { Field, NumberStepper, Suggestions, TagEditor } from '../components/form.jsx'
import { Badge, Button, ErrorBanner } from '../components/ui.jsx'
import { DEPARTMENTS } from '../lib/constants.js'
import { formatDate, localToday, logoColor } from '../lib/format.js'

const PAGE_SIZE = 12 // cards: 3 rows of 4 / 4 rows of 3

const STATUS_TONE = { upcoming: 'green', ongoing: 'indigo', completed: 'neutral', cancelled: 'red' }
const STATUS_OPTIONS = [
  ['', 'All statuses'],
  ['upcoming', 'Upcoming'],
  ['ongoing', 'Ongoing'],
  ['completed', 'Completed'],
  ['cancelled', 'Cancelled'],
]
const SKILL_SUGGESTIONS = ['Aptitude', 'Java', 'Python', 'SQL', 'DSA', 'Communication']

/**
 * Faculty: their department's drives + drives open to all; new drives are for their department.
 * Admin: every drive (department filter); new drives for chosen departments, none = all.
 */
export default function DrivesPage() {
  const { user } = useAuth()
  const showToast = useToast()
  const isAdmin = user.role === 'admin'
  const department = DEPARTMENTS[user.department_id]

  const [status, setStatus] = useState('upcoming')
  const [departmentId, setDepartmentId] = useState('')
  const [offset, setOffset] = useState(0)
  const [tick, setTick] = useState(0)
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  useEffect(() => {
    const request = { active: true }
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset })
    if (status) params.set('status', status)
    if (isAdmin && departmentId) params.set('department_id', departmentId)

    api(`/drives?${params}`)
      .then((data) => {
        if (!request.active) return
        setPage(data)
        setError('')
      })
      .catch((err) => request.active && setError(err.message))
      .finally(() => request.active && setLoading(false))
    return () => {
      request.active = false
    }
  }, [status, departmentId, offset, tick, isAdmin])

  const refetch = (changes) => {
    setLoading(true)
    changes?.()
    setTick((t) => t + 1)
  }

  const closeModal = useCallback(() => setModalOpen(false), [])
  const onCreated = useCallback(
    (drive) => {
      setModalOpen(false)
      showToast(`${drive.company} drive added`)
      setLoading(true)
      setOffset(0)
      setTick((t) => t + 1)
    },
    [showToast],
  )

  const items = page?.items ?? []
  const total = page?.total ?? 0
  const filtered = Boolean(departmentId) || status !== ''

  return (
    <div className="page drives-page">
      <div className="page-intro">
        <div>
          <h2>Placement drives</h2>
          <p>
            {isAdmin
              ? 'Create and manage campus opportunities for every department.'
              : `Create and manage campus opportunities for ${department?.code ?? 'your'} students.`}
          </p>
        </div>
        <Button icon="plus" onClick={() => setModalOpen(true)}>
          Add Drive
        </Button>
      </div>

      <div className="drives-toolbar">
        <div className="status-tabs" role="tablist" aria-label="Filter by status">
          {STATUS_OPTIONS.map(([value, label]) => (
            <button
              key={value || 'all'}
              type="button"
              role="tab"
              aria-selected={status === value}
              className={status === value ? 'selected' : ''}
              onClick={() =>
                refetch(() => {
                  setStatus(value)
                  setOffset(0)
                })
              }
            >
              {label}
            </button>
          ))}
        </div>
        <div className="toolbar-right">
          {isAdmin ? (
            <select
              className="input compact"
              aria-label="Filter by department"
              value={departmentId}
              onChange={(e) =>
                refetch(() => {
                  setDepartmentId(e.target.value)
                  setOffset(0)
                })
              }
            >
              <option value="">All departments</option>
              {Object.entries(DEPARTMENTS).map(([id, d]) => (
                <option key={id} value={id}>
                  {d.code}
                </option>
              ))}
            </select>
          ) : (
            department && <Badge tone="indigo">{department.code} + open to all</Badge>
          )}
          {page && (
            <span className="muted-text">
              {total} {total === 1 ? 'drive' : 'drives'}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="card table-message">
          <ErrorBanner>{error}</ErrorBanner>
          <Button variant="secondary" onClick={() => refetch(() => setError(''))}>
            Try again
          </Button>
        </div>
      )}

      {!error && !page && (
        <div className="page-loading" role="status" aria-label="Loading drives">
          <span className="button-spinner" aria-hidden="true" />
        </div>
      )}

      {!error && page && items.length === 0 && (
        <div className="card empty-mini">
          <div className="empty-art">
            <Icon name="briefcase" size={30} />
          </div>
          <h3>{status ? `No ${status} drives` : 'No drives yet'}</h3>
          <p>
            {filtered
              ? 'Try another status or department, or add a new drive.'
              : 'Add a placement drive so eligible students see it on their dashboard.'}
          </p>
          <Button icon="plus" onClick={() => setModalOpen(true)}>
            Add Drive
          </Button>
        </div>
      )}

      {!error && items.length > 0 && (
        <div className={`drive-grid ${loading ? 'is-refreshing' : ''}`} aria-busy={loading}>
          {items.map((d) => (
            <DriveCard key={d.id} drive={d} />
          ))}
        </div>
      )}

      {!error && total > PAGE_SIZE && (
        <div className="card pagination drives-pagination">
          <span>
            Showing {offset + 1}–{offset + items.length} of {total} drives
          </span>
          <div>
            <Button
              variant="secondary"
              disabled={loading || offset === 0}
              onClick={() => refetch(() => setOffset(Math.max(0, offset - PAGE_SIZE)))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={loading || offset + items.length >= total}
              onClick={() => refetch(() => setOffset(offset + PAGE_SIZE))}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {modalOpen && (
        <DriveModal isAdmin={isAdmin} ownDepartment={department} onClose={closeModal} onCreated={onCreated} />
      )}
    </div>
  )
}

function DriveCard({ drive: d }) {
  const today = localToday()
  const datePassed = d.status === 'upcoming' && d.drive_date < today
  const registrationClosed = d.registration_deadline && d.registration_deadline < today

  return (
    <article className="card drive-card">
      <div className="drive-card-head">
        <span className="company-logo large-logo" style={{ background: logoColor(d.company) }}>
          {d.company.trim()[0]?.toUpperCase()}
        </span>
        <div>
          <Badge tone={datePassed ? 'amber' : STATUS_TONE[d.status]}>
            {datePassed ? 'Date passed' : capitalize(d.status)}
          </Badge>
          <h3>{d.company}</h3>
          <p>{d.job_role}</p>
        </div>
      </div>

      <div className="drive-date">
        <Icon name="calendar" size={17} />
        <span>
          <small>Drive date</small>
          <strong>{formatDate(d.drive_date)}</strong>
        </span>
        <span className="drive-location">
          <small>Location</small>
          <strong>{d.location || 'Not specified'}</strong>
        </span>
      </div>

      <div className="criteria">
        <div>
          <span>Minimum CGPA</span>
          <strong>{d.min_cgpa.toFixed(2)} / 10</strong>
        </div>
        <div>
          <span>Max backlogs</span>
          <strong>{d.max_backlogs}</strong>
        </div>
        <div>
          <span>Package</span>
          <strong>{d.package_lpa !== null ? `₹${d.package_lpa} LPA` : 'Not disclosed'}</strong>
        </div>
      </div>

      <div className="drive-tags">
        <span>Eligible</span>
        <div>
          {d.departments.length ? (
            d.departments.map((code) => (
              <span className="chip simple" key={code}>
                {code}
              </span>
            ))
          ) : (
            <span className="chip simple">All departments</span>
          )}
          <span className="chip simple">{d.passing_year ? `Batch ${d.passing_year}` : 'Any batch'}</span>
        </div>
      </div>

      <div className="drive-tags">
        <span>Required skills</span>
        <div>
          {d.required_skills.length ? (
            d.required_skills.map((s) => (
              <span className="chip simple" key={s}>
                {s}
              </span>
            ))
          ) : (
            <span className="muted-text">None listed</span>
          )}
        </div>
      </div>

      {d.description && <p className="drive-description">{d.description}</p>}

      <div className="drive-card-foot">
        <Icon name="clock" size={14} />
        {d.registration_deadline ? (
          <span className={registrationClosed ? 'closed' : ''}>
            Registration {registrationClosed ? 'closed' : 'closes'} {formatDate(d.registration_deadline)}
          </span>
        ) : (
          <span>No registration deadline</span>
        )}
      </div>
    </article>
  )
}

const EMPTY_FORM = {
  company: '',
  job_role: '',
  location: '',
  package_lpa: '',
  min_cgpa: '',
  max_backlogs: 0,
  passing_year: '',
  description: '',
  required_skills: [],
  drive_date: '',
  registration_deadline: '',
  department_ids: [],
}

function DriveModal({ isAdmin, ownDepartment, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [saving, setSaving] = useState(false)
  const today = localToday()

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && !saving && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, saving])

  const update = (name, value) => {
    setForm((f) => ({ ...f, [name]: value }))
    setErrors((e) => ({ ...e, [name]: '' }))
    setServerError('')
  }

  const toggleDepartment = (id) =>
    update(
      'department_ids',
      form.department_ids.includes(id) ? form.department_ids.filter((x) => x !== id) : [...form.department_ids, id],
    )

  const submit = async (e) => {
    e.preventDefault()
    if (saving) return
    const next = validate(form, today)
    setErrors(next)
    if (Object.keys(next).length) {
      document.getElementById(Object.keys(next)[0])?.focus()
      return
    }
    setSaving(true)
    try {
      const drive = await api('/drives', { method: 'POST', body: toPayload(form) })
      onCreated(drive)
    } catch (err) {
      setServerError(err.message)
      setSaving(false)
    }
  }

  const inputProps = (name) => ({
    id: name,
    className: `input ${errors[name] ? 'input-error' : ''}`,
    value: form[name],
    disabled: saving,
    'aria-invalid': Boolean(errors[name]),
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    onChange: (e) => update(name, e.target.value),
  })

  return (
    <div className="modal-layer">
      <div className="modal-backdrop" onClick={() => !saving && onClose()} />
      <form
        className="modal drive-modal"
        onSubmit={submit}
        noValidate
        role="dialog"
        aria-modal="true"
        aria-labelledby="drive-modal-title"
      >
        <div className="modal-head">
          <div>
            <p className="overline">NEW OPPORTUNITY</p>
            <h2 id="drive-modal-title">Add placement drive</h2>
            <p>Define the role and eligibility criteria. Eligible students see it on their dashboard.</p>
          </div>
          <button type="button" className="icon-btn" disabled={saving} onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        <div className="modal-body">
          <ErrorBanner>{serverError}</ErrorBanner>

          <div className="form-grid">
            <Field label="Company name *" htmlFor="company" error={errors.company}>
              <input {...inputProps('company')} placeholder="e.g. Wipro" maxLength={120} autoFocus />
            </Field>
            <Field label="Job role *" htmlFor="job_role" error={errors.job_role}>
              <input {...inputProps('job_role')} placeholder="e.g. Project Engineer" maxLength={120} />
            </Field>
            <Field label="Location" htmlFor="location">
              <input {...inputProps('location')} placeholder="e.g. Pune" maxLength={120} />
            </Field>
            <Field label="Package (LPA)" htmlFor="package_lpa" error={errors.package_lpa} hint="Leave empty if not disclosed">
              <input {...inputProps('package_lpa')} type="number" inputMode="decimal" min="0" step="0.01" placeholder="e.g. 6.50" />
            </Field>
          </div>

          <h4 className="modal-subhead">Eligibility</h4>
          <div className="form-grid">
            <Field label="Minimum CGPA" htmlFor="min_cgpa" error={errors.min_cgpa} hint="Empty = no cutoff">
              <input {...inputProps('min_cgpa')} type="number" inputMode="decimal" min="0" max="10" step="0.01" placeholder="e.g. 7.00" />
            </Field>
            <Field label="Passing year (batch)" htmlFor="passing_year" error={errors.passing_year} hint="Empty = any batch">
              <input {...inputProps('passing_year')} type="number" inputMode="numeric" min="2000" max="2100" placeholder="e.g. 2027" />
            </Field>
          </div>
          <NumberStepper
            id="max_backlogs"
            label="Maximum active backlogs"
            value={form.max_backlogs}
            max={50}
            onChange={(v) => update('max_backlogs', v)}
          />

          <Field label="Eligible departments" htmlFor="departments">
            {isAdmin ? (
              <>
                <div className="choice-chips" id="departments" role="group" aria-label="Eligible departments">
                  {Object.entries(DEPARTMENTS).map(([id, d]) => {
                    const selected = form.department_ids.includes(Number(id))
                    return (
                      <button
                        type="button"
                        key={id}
                        className={selected ? 'selected' : ''}
                        aria-pressed={selected}
                        disabled={saving}
                        onClick={() => toggleDepartment(Number(id))}
                      >
                        {selected && <Icon name="check" size={13} />} {d.code}
                      </button>
                    )
                  })}
                </div>
                <small className="field-note">
                  {form.department_ids.length ? '' : 'None selected = open to all departments'}
                </small>
              </>
            ) : (
              <div className="choice-chips" id="departments">
                <button type="button" className="selected" disabled>
                  <Icon name="lock" size={13} /> {ownDepartment?.code ?? 'Your department'}
                </button>
                <small className="field-note">Faculty drives are for your own department.</small>
              </div>
            )}
          </Field>

          <Field label="Required skills" htmlFor="required_skills" hint="Used to match students and suggest skills to learn">
            <TagEditor
              id="required_skills"
              tags={form.required_skills}
              onChange={(v) => update('required_skills', v)}
              placeholder="Type a skill and press Enter"
            />
            <Suggestions
              options={SKILL_SUGGESTIONS}
              tags={form.required_skills}
              onAdd={(s) => update('required_skills', [...form.required_skills, s])}
            />
          </Field>

          <div className="form-grid">
            <Field label="Drive date *" htmlFor="drive_date" error={errors.drive_date}>
              <input {...inputProps('drive_date')} type="date" min={today} />
            </Field>
            <Field label="Registration deadline" htmlFor="registration_deadline" error={errors.registration_deadline}>
              <input {...inputProps('registration_deadline')} type="date" min={today} max={form.drive_date || undefined} />
            </Field>
          </div>

          <Field label="Description" htmlFor="description" error={errors.description}>
            <textarea
              {...inputProps('description')}
              className={`input textarea ${errors.description ? 'input-error' : ''}`}
              rows={3}
              maxLength={5000}
              placeholder="Role responsibilities, selection rounds, important details..."
            />
          </Field>
        </div>

        <div className="modal-actions">
          <Button variant="secondary" type="button" disabled={saving} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {saving ? 'Adding...' : 'Add drive'}
          </Button>
        </div>
      </form>
    </div>
  )
}

/** Mirrors the backend DriveCreate rules so most mistakes are caught before the request. */
function validate(f, today) {
  const errors = {}
  if (!f.company.trim()) errors.company = 'Enter the company name'
  if (!f.job_role.trim()) errors.job_role = 'Enter the job role'

  if (f.package_lpa !== '' && !(/^\d{1,4}(\.\d{1,2})?$/.test(f.package_lpa)))
    errors.package_lpa = 'Up to 9999.99, max 2 decimals'
  if (f.min_cgpa !== '' && (!/^\d{1,2}(\.\d{1,2})?$/.test(f.min_cgpa) || Number(f.min_cgpa) > 10))
    errors.min_cgpa = 'Between 0 and 10, max 2 decimals'
  if (f.passing_year !== '' && (!/^\d{4}$/.test(f.passing_year) || f.passing_year < '2000' || f.passing_year > '2100'))
    errors.passing_year = 'Enter a year like 2027'

  if (!f.drive_date) errors.drive_date = 'Select the drive date'
  else if (f.drive_date < today) errors.drive_date = "Drive date can't be in the past"
  if (f.registration_deadline && f.drive_date && f.registration_deadline > f.drive_date)
    errors.registration_deadline = 'Must be on or before the drive date'
  return errors
}

function toPayload(f) {
  const num = (s) => (s === '' ? null : Number(s))
  const text = (s) => (s.trim() ? s.trim() : null)
  return {
    company: f.company.trim(),
    job_role: f.job_role.trim(),
    location: text(f.location),
    package_lpa: num(f.package_lpa),
    min_cgpa: f.min_cgpa === '' ? 0 : Number(f.min_cgpa),
    max_backlogs: f.max_backlogs,
    passing_year: num(f.passing_year),
    description: text(f.description),
    required_skills: f.required_skills,
    drive_date: f.drive_date,
    registration_deadline: f.registration_deadline || null,
    department_ids: f.department_ids, // faculty: [] -> backend uses their department
  }
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
