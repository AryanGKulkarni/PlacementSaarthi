import { useEffect, useRef, useState } from 'react'

import { api } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { useToast } from '../components/Toast.jsx'
import { Field, NumberStepper, Suggestions, TagEditor } from '../components/form.jsx'
import { Button, ErrorBanner } from '../components/ui.jsx'

const RESUME_MAX_MB = 5 // backend: settings.max_resume_mb

const SKILL_SUGGESTIONS = ['Java', 'Python', 'SQL', 'DSA', 'React', 'JavaScript', 'Git']
const INTEREST_SUGGESTIONS = [
  'Backend development',
  'Frontend development',
  'Data analytics',
  'Cloud engineering',
  'Machine learning',
]

// Same 9 fields and labels as the backend's completeness (services/readiness.py PROFILE_FIELDS).
// `target` is the element the "Missing" chips scroll to.
const COMPLETENESS = [
  { label: 'Roll number', target: 'field-roll_no', empty: (f) => !f.roll_no.trim() },
  { label: 'Current year', target: 'field-year', empty: (f) => !f.year },
  { label: 'Passing year', target: 'field-passing_year', empty: (f) => !f.passing_year },
  { label: 'CGPA', target: 'field-cgpa', empty: (f) => f.cgpa === '' },
  { label: '10th %', target: 'field-tenth_percent', empty: (f) => f.tenth_percent === '' },
  { label: '12th %', target: 'field-twelfth_percent', empty: (f) => f.twelfth_percent === '' },
  { label: 'Skills', target: 'field-skills', empty: (f) => !f.skills.length },
  { label: 'Career interests', target: 'field-interests', empty: (f) => !f.interests.length },
  { label: 'Resume', target: 'resume-section', empty: (_, hasResume) => !hasResume },
]

export default function ProfilePage() {
  const [profile, setProfile] = useState(null) // last saved state from the API
  const [loadError, setLoadError] = useState('')
  const [attempt, setAttempt] = useState(0) // bump to retry

  useEffect(() => {
    let active = true
    api('/students/me/profile')
      .then((p) => active && setProfile(p))
      .catch((err) => active && setLoadError(err.message))
    return () => {
      active = false
    }
  }, [attempt])

  const retry = () => {
    setLoadError('')
    setAttempt((n) => n + 1)
  }

  if (loadError) {
    return (
      <div className="page profile-page">
        <ErrorBanner>{loadError}</ErrorBanner>
        <Button variant="secondary" onClick={retry}>
          Try again
        </Button>
      </div>
    )
  }
  if (!profile) {
    return (
      <div className="page-loading" role="status" aria-label="Loading profile">
        <span className="button-spinner" aria-hidden="true" />
      </div>
    )
  }
  return <ProfileForm profile={profile} onSaved={setProfile} />
}

function ProfileForm({ profile, onSaved }) {
  const { updateUser } = useAuth()
  const showToast = useToast()
  const [form, setForm] = useState(() => toForm(profile))
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [saving, setSaving] = useState(false)

  const patch = buildPatch(form, profile)
  const dirty = Object.keys(patch).length > 0

  const missing = COMPLETENESS.filter((c) => c.empty(form, profile.has_resume))
  const isMissing = (label) => missing.some((m) => m.label === label)
  const total = COMPLETENESS.length
  const filled = total - missing.length
  const percent = Math.round((100 * filled) / total)

  // Browser warning when closing/refreshing the tab with unsaved edits.
  useEffect(() => {
    if (!dirty) return
    const warn = (e) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const update = (name, value) => {
    setForm((f) => ({ ...f, [name]: value }))
    setErrors((e) => ({ ...e, [name]: '' }))
    setServerError('')
  }

  const reset = () => {
    setForm(toForm(profile))
    setErrors({})
    setServerError('')
  }

  const save = async (e) => {
    e.preventDefault()
    if (saving || !dirty) return
    const next = validate(form)
    setErrors(next)
    if (Object.keys(next).length) {
      document.getElementById(`field-${Object.keys(next)[0]}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setSaving(true)
    try {
      const saved = await api('/students/me/profile', { method: 'PATCH', body: patch })
      onSaved(saved)
      setForm(toForm(saved)) // pick up server-side cleanup (uppercased roll no, trimmed tags...)
      updateUser({ full_name: saved.full_name })
      showToast('Profile updated – your readiness score has been refreshed')
    } catch (err) {
      setServerError(err.message)
      if (err.status === 409) setErrors({ roll_no: 'Already used by another student' })
    } finally {
      setSaving(false)
    }
  }

  const inputProps = (name) => ({
    id: name,
    className: `input ${errors[name] ? 'input-error' : ''}`,
    value: form[name],
    'aria-invalid': Boolean(errors[name]),
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    onChange: (e) => update(name, e.target.value),
  })

  const scrollTo = (target) => {
    const el = document.getElementById(target)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el?.querySelector('input, select, button')?.focus({ preventScroll: true })
  }

  return (
    <div className={`page profile-page ${dirty ? 'has-sticky-actions' : ''}`}>
      <div className="page-intro">
        <div>
          <h2>Student profile</h2>
          <p>Keep your academic details complete to improve placement matching.</p>
        </div>
      </div>

      <section className="card completeness-card">
        <div className="completeness-copy">
          <div className="completeness-icon">
            <Icon name="user" size={20} />
          </div>
          <div>
            <div className="completeness-title">
              <h3>
                Profile {filled} of {total} complete
              </h3>
              <strong>{percent}%</strong>
            </div>
            <div
              className="profile-progress"
              role="progressbar"
              aria-label="Profile completeness"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <i style={{ width: `${percent}%` }} />
            </div>
            <p>
              {missing.length
                ? 'Complete the missing details to unlock more eligible opportunities.'
                : 'Your profile is complete. Keep it up to date as you learn new skills.'}
            </p>
          </div>
        </div>
        {missing.length > 0 && (
          <div className="missing-fields">
            <span>Missing</span>
            {missing.map((item) => (
              <button type="button" key={item.target} onClick={() => scrollTo(item.target)}>
                {item.label}
                <Icon name="chevron" size={12} />
              </button>
            ))}
          </div>
        )}
      </section>

      <form className="profile-form" onSubmit={save} noValidate>
        <ErrorBanner>{serverError}</ErrorBanner>

        <section className="card profile-section">
          <SectionHead number={1} title="Personal details" text="Basic information used in your placement profile." />
          <div className="form-grid three">
            <Field label="Full name" htmlFor="full_name" id="field-full_name" error={errors.full_name}>
              <input {...inputProps('full_name')} autoComplete="name" maxLength={120} />
            </Field>
            <Field label="Email address" htmlFor="email" hint="Contact admin to change email">
              <div className="locked-input" title="Contact admin to change email">
                <input id="email" className="input" type="email" value={profile.email} readOnly />
                <Icon name="lock" size={15} />
              </div>
            </Field>
            <Field
              label="Roll number"
              htmlFor="roll_no"
              id="field-roll_no"
              error={errors.roll_no}
              missing={isMissing('Roll number')}
            >
              <input {...inputProps('roll_no')} placeholder="e.g. CS21B045" maxLength={30} />
            </Field>
          </div>
        </section>

        <section className="card profile-section">
          <SectionHead number={2} title="Academic details" text="Your academic record determines drive eligibility." />
          <div className="form-grid three">
            <Field label="Branch" htmlFor="branch" hint="Managed by the college">
              <select id="branch" className="input readonly-select" value="" disabled>
                <option value="">
                  {profile.department_code} – {profile.department_name}
                </option>
              </select>
            </Field>
            <Field
              label="Passing year"
              htmlFor="passing_year"
              id="field-passing_year"
              missing={isMissing('Passing year')}
            >
              <select {...inputProps('passing_year')}>
                <option value="">Select year</option>
                {passingYearOptions(form.passing_year).map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="CGPA"
              htmlFor="cgpa"
              id="field-cgpa"
              hint="Out of 10"
              error={errors.cgpa}
              missing={isMissing('CGPA')}
            >
              <input {...inputProps('cgpa')} type="number" inputMode="decimal" min="0" max="10" step="0.01" placeholder="0.00" />
            </Field>
          </div>

          <Field label="Current year" htmlFor="year-1" id="field-year" missing={isMissing('Current year')}>
            <div className="year-segments" role="group" aria-label="Current year">
              {[1, 2, 3, 4].map((y) => (
                <button
                  key={y}
                  id={`year-${y}`}
                  type="button"
                  className={form.year === y ? 'selected' : ''}
                  aria-pressed={form.year === y}
                  onClick={() => update('year', y)}
                >
                  {ordinal(y)}
                </button>
              ))}
            </div>
          </Field>

          <div className="form-grid three academic-secondary">
            <NumberStepper
              id="active_backlogs"
              label="Active backlogs"
              value={form.active_backlogs}
              max={50}
              onChange={(v) => update('active_backlogs', v)}
            />
            <Field
              label="10th percentage"
              htmlFor="tenth_percent"
              id="field-tenth_percent"
              error={errors.tenth_percent}
              missing={isMissing('10th %')}
            >
              <PercentInput {...inputProps('tenth_percent')} />
            </Field>
            <Field
              label="12th / Diploma percentage"
              htmlFor="twelfth_percent"
              id="field-twelfth_percent"
              error={errors.twelfth_percent}
              missing={isMissing('12th %')}
            >
              <PercentInput {...inputProps('twelfth_percent')} />
            </Field>
          </div>
        </section>

        <section className="card profile-section">
          <SectionHead number={3} title="Skills & interests" text="Help us understand the roles that best fit you." />
          <Field
            label="Skills"
            htmlFor="skills"
            id="field-skills"
            hint="Type a skill and press Enter to add it."
            missing={isMissing('Skills')}
          >
            <TagEditor
              id="skills"
              tags={form.skills}
              onChange={(v) => update('skills', v)}
              placeholder="Type a skill and press Enter"
            />
            <Suggestions
              options={SKILL_SUGGESTIONS}
              tags={form.skills}
              onAdd={(s) => update('skills', [...form.skills, s])}
            />
          </Field>
          <Field
            label="Career interests"
            htmlFor="interests"
            id="field-interests"
            hint="Add the types of roles you want to explore."
            missing={isMissing('Career interests')}
          >
            <TagEditor
              id="interests"
              tags={form.interests}
              onChange={(v) => update('interests', v)}
              placeholder="e.g. Backend development"
            />
            <Suggestions
              options={INTEREST_SUGGESTIONS}
              tags={form.interests}
              onAdd={(s) => update('interests', [...form.interests, s])}
            />
          </Field>
        </section>

        <section className="card profile-section">
          <SectionHead number={4} title="Experience" text="Add your practical learning and achievements." />
          <div className="experience-grid">
            <NumberStepper
              compact
              id="internships"
              label="Internships"
              value={form.internships}
              max={50}
              onChange={(v) => update('internships', v)}
            />
            <NumberStepper
              compact
              id="projects"
              label="Projects"
              value={form.projects}
              max={100}
              onChange={(v) => update('projects', v)}
            />
            <NumberStepper
              compact
              id="certifications"
              label="Certifications"
              value={form.certifications}
              max={100}
              onChange={(v) => update('certifications', v)}
            />
          </div>
        </section>

        <ResumeSection hasResume={profile.has_resume} onChange={onSaved} />

        {dirty && (
          <div className="profile-save-bar">
            <span>You have unsaved changes</span>
            <div>
              <Button variant="secondary" type="button" onClick={reset} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {saving ? 'Saving...' : 'Save changes'}
              </Button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}

/**
 * Resume is saved immediately (its own endpoints), separate from the Save bar.
 * The API returns the full profile; we only take has_resume/completeness from it via onChange,
 * unsaved form edits are kept because the form state is separate.
 */
function ResumeSection({ hasResume, onChange }) {
  const showToast = useToast()
  const input = useRef(null)
  const [busy, setBusy] = useState('') // 'upload' | 'view' | 'delete'
  const [error, setError] = useState('')
  const [confirmRemove, setConfirmRemove] = useState(false)

  const upload = async (file) => {
    if (!file || busy) return
    setError('')
    if (!file.name.toLowerCase().endsWith('.pdf')) return setError('Resume must be a PDF file')
    if (file.size > RESUME_MAX_MB * 1024 * 1024) return setError(`Resume must be under ${RESUME_MAX_MB} MB`)

    const body = new FormData()
    body.append('file', file)
    setBusy('upload')
    try {
      onChange(await api('/students/me/resume', { method: 'PUT', body }))
      showToast(hasResume ? 'Resume replaced' : 'Resume uploaded')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
      if (input.current) input.current.value = '' // allow picking the same file again
    }
  }

  const view = async () => {
    // Open the tab now (inside the click) so popup blockers allow it, then load the PDF into it.
    const tab = window.open('', '_blank')
    setBusy('view')
    setError('')
    try {
      const blob = await api('/students/me/resume', { responseType: 'blob' })
      const url = URL.createObjectURL(blob)
      if (tab) tab.location.href = url
      else window.location.assign(url)
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      tab?.close()
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const remove = async () => {
    setBusy('delete')
    setError('')
    try {
      onChange(await api('/students/me/resume', { method: 'DELETE' }))
      showToast('Resume removed')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
      setConfirmRemove(false)
    }
  }

  const pick = () => input.current?.click()

  return (
    <section id="resume-section" className={`card profile-section ${!hasResume ? 'resume-missing' : ''}`}>
      <SectionHead number={5} title="Resume" text="Upload your latest resume for placement applications." />
      <input
        ref={input}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        onChange={(e) => upload(e.target.files?.[0])}
      />
      <ErrorBanner>{error}</ErrorBanner>

      {hasResume ? (
        <div className="resume-file">
          <div className="resume-file-icon">
            <Icon name="file" size={21} />
          </div>
          <div>
            <strong>resume.pdf</strong>
            <span>PDF · Replacing it overwrites the current file</span>
          </div>
          <div className="resume-actions">
            {confirmRemove ? (
              <>
                <button type="button" onClick={() => setConfirmRemove(false)} disabled={Boolean(busy)}>
                  Keep
                </button>
                <button type="button" className="remove" onClick={remove} disabled={Boolean(busy)}>
                  {busy === 'delete' ? 'Removing...' : 'Confirm remove'}
                </button>
              </>
            ) : (
              <>
                <button type="button" onClick={view} disabled={Boolean(busy)}>
                  {busy === 'view' ? 'Opening...' : 'View'}
                </button>
                <button type="button" onClick={pick} disabled={Boolean(busy)}>
                  {busy === 'upload' ? 'Uploading...' : 'Replace'}
                </button>
                <button type="button" className="remove" onClick={() => setConfirmRemove(true)} disabled={Boolean(busy)}>
                  Remove
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div
          className="resume-upload"
          role="button"
          tabIndex={0}
          aria-busy={busy === 'upload'}
          onClick={pick}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              pick()
            }
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            upload(e.dataTransfer.files[0])
          }}
        >
          <div className="upload-icon">
            <Icon name="upload" size={22} />
          </div>
          <div>
            <strong>{busy === 'upload' ? 'Uploading...' : 'Upload your resume'}</strong>
            <span>Drag and drop or browse · PDF, max {RESUME_MAX_MB} MB</span>
          </div>
          <Button variant="secondary" type="button" loading={busy === 'upload'} tabIndex={-1}>
            Choose file
          </Button>
        </div>
      )}
      {!hasResume && <span className="not-filled-hint">Not filled</span>}
    </section>
  )
}

function SectionHead({ number, title, text }) {
  return (
    <div className="form-section-head">
      <div className="section-number">{number}</div>
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </div>
  )
}

function PercentInput(props) {
  return (
    <div className="suffix-input">
      <input {...props} type="number" inputMode="decimal" min="0" max="100" step="0.01" placeholder="0.00" />
      <span>%</span>
    </div>
  )
}

// ---- helpers --------------------------------------------------------------------------------

/** API profile -> form state. Number inputs hold strings so they can be empty. */
function toForm(p) {
  const str = (n) => (n === null || n === undefined ? '' : String(n))
  return {
    full_name: p.full_name,
    roll_no: p.roll_no ?? '',
    year: p.year,
    passing_year: str(p.passing_year),
    cgpa: str(p.cgpa),
    active_backlogs: p.active_backlogs,
    tenth_percent: str(p.tenth_percent),
    twelfth_percent: str(p.twelfth_percent),
    skills: p.skills,
    interests: p.interests,
    internships: p.internships,
    projects: p.projects,
    certifications: p.certifications,
  }
}

/** Form state -> API values ('' becomes null so the field is cleared). */
function toApi(f) {
  const num = (s) => (s === '' ? null : Number(s))
  return {
    full_name: f.full_name.replace(/\s+/g, ' ').trim(),
    roll_no: f.roll_no.trim() ? f.roll_no.trim().toUpperCase() : null,
    year: f.year,
    passing_year: num(f.passing_year),
    cgpa: num(f.cgpa),
    active_backlogs: f.active_backlogs,
    tenth_percent: num(f.tenth_percent),
    twelfth_percent: num(f.twelfth_percent),
    skills: f.skills,
    interests: f.interests,
    internships: f.internships,
    projects: f.projects,
    certifications: f.certifications,
  }
}

/** PATCH body: only fields that differ from the saved profile. */
function buildPatch(form, profile) {
  const next = toApi(form)
  const patch = {}
  for (const [key, value] of Object.entries(next)) {
    if (JSON.stringify(value) !== JSON.stringify(profile[key] ?? null)) patch[key] = value
  }
  return patch
}

/** Client-side checks matching the backend's StudentProfileUpdate limits. */
function validate(f) {
  const errors = {}
  if (f.full_name.trim().length < 2) errors.full_name = 'Enter your full name'
  const decimal = (value, max, name, label) => {
    if (value === '') return
    if (!/^\d+(\.\d{1,2})?$/.test(value) || Number(value) > max)
      errors[name] = `${label} must be between 0 and ${max}, up to 2 decimals`
  }
  decimal(f.cgpa, 10, 'cgpa', 'CGPA')
  decimal(f.tenth_percent, 100, 'tenth_percent', 'Percentage')
  decimal(f.twelfth_percent, 100, 'twelfth_percent', 'Percentage')
  return errors
}

/** Last year .. 5 years ahead, plus the saved value if it's outside that range. */
function passingYearOptions(current) {
  const now = new Date().getFullYear()
  const years = Array.from({ length: 7 }, (_, i) => now - 1 + i)
  const saved = Number(current)
  if (saved && !years.includes(saved)) years.push(saved)
  return years.sort((a, b) => a - b)
}

function ordinal(n) {
  return `${n}${{ 1: 'st', 2: 'nd', 3: 'rd' }[n] ?? 'th'}`
}
