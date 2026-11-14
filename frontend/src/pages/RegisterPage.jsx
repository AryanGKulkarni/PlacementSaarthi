import { useState } from 'react'

import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { Button, ErrorBanner, FormField, Logo } from '../components/ui.jsx'
import { APP_NAME, DEPARTMENTS, DESIGNATIONS } from '../lib/constants.js'
import { navigate } from '../lib/router.js'
import { homeFor } from '../routes.js'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_MAX_BYTES = 72 // bcrypt limit, enforced by the backend too

const ROLE_OPTIONS = [
  {
    role: 'student',
    icon: 'graduation',
    title: 'Student',
    caption: 'Track your placement readiness, see eligible drives, ask the assistant',
  },
  {
    role: 'faculty',
    icon: 'briefcase',
    title: 'Faculty',
    caption: "Manage drives, upload documents, view your department's students",
  },
]

const EMPTY = {
  fullName: '',
  email: '',
  departmentId: '',
  password: '',
  confirmPassword: '',
  employeeId: '',
  designation: '',
  phone: '',
  joinedOn: '',
}

export default function RegisterPage() {
  const { register } = useAuth()
  const [role, setRole] = useState('student')
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const today = localDate()
  const isFaculty = role === 'faculty'
  const strength = passwordStrength(values.password)

  const update = (name, value) => {
    setValues((v) => ({ ...v, [name]: value }))
    setErrors((e) => ({ ...e, [name]: '' }))
    setServerError('')
  }

  const selectRole = (next) => {
    setRole(next)
    setErrors({})
    setServerError('')
  }

  const validate = () => {
    const v = values
    const next = {}
    if (v.fullName.trim().length < 2) next.fullName = 'Enter your full name'
    if (!EMAIL_RE.test(v.email.trim())) next.email = 'Enter a valid email'
    if (!v.departmentId) next.departmentId = 'Select your department'
    if (v.password.length < 8) next.password = 'Password must be at least 8 characters'
    else if (new TextEncoder().encode(v.password).length > PASSWORD_MAX_BYTES)
      next.password = 'Password is too long'
    if (!v.confirmPassword) next.confirmPassword = 'Confirm your password'
    else if (v.password !== v.confirmPassword) next.confirmPassword = "Passwords don't match"

    if (isFaculty) {
      if (!v.employeeId.trim()) next.employeeId = 'Enter your employee ID'
      if (!v.designation) next.designation = 'Select your designation'
      if (!/^\d{10}$/.test(v.phone)) next.phone = 'Phone must be 10 digits'
      if (!v.joinedOn) next.joinedOn = 'Select your joining date'
      else if (v.joinedOn > today) next.joinedOn = "Joining date can't be in the future"
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (e) => {
    e.preventDefault()
    if (loading || !validate()) return
    setLoading(true)
    try {
      const user = await register(toPayload(role, values))
      navigate(homeFor(user.role), { replace: true })
    } catch (err) {
      setServerError(err.message)
      // Point at the field the server complained about.
      if (err.status === 409 && /email/i.test(err.message)) setErrors({ email: 'Already registered' })
      if (err.status === 409 && /employee/i.test(err.message)) setErrors({ employeeId: 'Already registered' })
      setLoading(false)
    }
  }

  // Shared props for a text-like input with error styling + aria wiring.
  const inputProps = (name) => ({
    id: name,
    className: `input ${errors[name] ? 'input-error' : ''}`,
    value: values[name],
    'aria-invalid': Boolean(errors[name]),
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    onChange: (e) => update(name, e.target.value),
  })

  return (
    <div className="auth-page register-page">
      <div className="auth-brand">
        <Logo />
        <p>AI-powered placement preparation for students.</p>
      </div>

      <div className="auth-card register-card">
        <div className="auth-head">
          <div className="auth-logo">
            <Icon name="user" size={23} />
          </div>
          <h1>Create your account</h1>
          <p>Who are you registering as?</p>
        </div>

        <form onSubmit={submit} noValidate>
          <ErrorBanner>{serverError}</ErrorBanner>

          <div className="role-cards" role="radiogroup" aria-label="Account type">
            {ROLE_OPTIONS.map((option) => {
              const selected = role === option.role
              return (
                <button
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  className={`role-card ${selected ? 'selected' : ''}`}
                  key={option.role}
                  onClick={() => selectRole(option.role)}
                >
                  <span className="role-icon">
                    <Icon name={option.icon} size={21} />
                  </span>
                  <span className="role-copy">
                    <strong>{option.title}</strong>
                    <small>{option.caption}</small>
                  </span>
                  {selected && (
                    <span className="role-check">
                      <Icon name="check" size={12} />
                    </span>
                  )}
                </button>
              )
            })}
          </div>
          <p className="admin-note">Admin accounts are created by the placement cell.</p>

          <div className="register-fields">
            <FormField label="Full name" htmlFor="fullName" error={errors.fullName} required>
              <input {...inputProps('fullName')} placeholder="Enter your full name" autoComplete="name" />
            </FormField>

            <FormField label="College email" htmlFor="email" error={errors.email} required>
              <input {...inputProps('email')} type="email" placeholder="you@college.edu" autoComplete="email" />
            </FormField>

            <FormField label="Department / Branch" htmlFor="departmentId" error={errors.departmentId} required>
              <select {...inputProps('departmentId')}>
                <option value="">Select department</option>
                {Object.entries(DEPARTMENTS).map(([id, d]) => (
                  <option value={id} key={id}>
                    {d.code} – {d.name}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField
              label="Password"
              htmlFor="password"
              error={errors.password}
              hint="At least 8 characters"
              required
            >
              <div className="password-input">
                <input
                  {...inputProps('password')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a password"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  <Icon name={showPassword ? 'eyeOff' : 'eye'} size={17} />
                </button>
              </div>
              <div className={`password-strength strength-${strength}`} aria-label={`Password strength ${strength} of 4`}>
                {[1, 2, 3, 4].map((level) => (
                  <i key={level} />
                ))}
              </div>
            </FormField>

            <FormField label="Confirm password" htmlFor="confirmPassword" error={errors.confirmPassword} required>
              <input
                {...inputProps('confirmPassword')}
                type={showPassword ? 'text' : 'password'}
                placeholder="Re-enter your password"
                autoComplete="new-password"
              />
            </FormField>
          </div>

          {/* Faculty fields stay mounted so the expand animation works; disabled when hidden. */}
          <div className={`faculty-expand ${isFaculty ? 'open' : ''}`}>
            <div>
              <section className="faculty-details" aria-hidden={!isFaculty}>
                <div className="faculty-details-head">
                  <span>
                    <Icon name="briefcase" size={17} />
                  </span>
                  <div>
                    <h2>Faculty details</h2>
                    <p>Tell us about your role at the institute.</p>
                  </div>
                </div>
                <div className="register-fields">
                  <FormField label="Employee ID" htmlFor="employeeId" error={errors.employeeId} required>
                    <input {...inputProps('employeeId')} placeholder="e.g. EMP1042" disabled={!isFaculty} />
                  </FormField>

                  <FormField label="Designation" htmlFor="designation" error={errors.designation} required>
                    <select {...inputProps('designation')} disabled={!isFaculty}>
                      <option value="">Select designation</option>
                      {DESIGNATIONS.map(([value, label]) => (
                        <option value={value} key={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </FormField>

                  <FormField label="Phone number" htmlFor="phone" error={errors.phone} required>
                    <div className={`phone-input ${errors.phone ? 'input-error' : ''}`}>
                      <span>+91</span>
                      <input
                        id="phone"
                        inputMode="numeric"
                        autoComplete="tel-national"
                        maxLength={10}
                        value={values.phone}
                        placeholder="98765 43210"
                        disabled={!isFaculty}
                        aria-invalid={Boolean(errors.phone)}
                        aria-describedby={errors.phone ? 'phone-error' : undefined}
                        onChange={(e) => update('phone', e.target.value.replace(/\D/g, '').slice(0, 10))}
                      />
                    </div>
                  </FormField>

                  <FormField label="Joining date" htmlFor="joinedOn" error={errors.joinedOn} required>
                    <input {...inputProps('joinedOn')} type="date" max={today} disabled={!isFaculty} />
                  </FormField>
                </div>
              </section>
            </div>
          </div>

          {!isFaculty && (
            <div className="student-info">
              <Icon name="info" size={17} />
              <p>You can add your CGPA, skills, resume and other details from your profile after signing up.</p>
            </div>
          )}

          <Button className="full-btn auth-submit" type="submit" loading={loading}>
            {loading ? 'Creating account...' : `Create ${role} account`}
          </Button>
        </form>

        <div className="auth-switch">
          Already have an account?{' '}
          <button type="button" onClick={() => navigate('/login')}>
            Log in
          </button>
        </div>
      </div>

      <p className="auth-footer">{APP_NAME} · Placement Cell</p>
    </div>
  )
}

/** Form values -> backend RegisterRequest (snake_case, only the fields for this role). */
function toPayload(role, v) {
  const base = {
    role,
    full_name: v.fullName.trim(),
    email: v.email.trim(),
    password: v.password,
    department_id: Number(v.departmentId),
  }
  if (role !== 'faculty') return base
  return {
    ...base,
    employee_id: v.employeeId.trim(),
    designation: v.designation,
    phone: `+91${v.phone}`,
    joined_on: v.joinedOn,
  }
}

/** 0-4: length 8+, uppercase, digit, symbol (same rule as the Figma design). */
function passwordStrength(password) {
  return [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length
}

/** Today as YYYY-MM-DD in the user's timezone (toISOString would use UTC). */
function localDate() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
