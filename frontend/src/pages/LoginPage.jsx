import { useState } from 'react'

import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { Button, ErrorBanner, FormField, Logo } from '../components/ui.jsx'
import { APP_NAME } from '../lib/constants.js'
import { navigate } from '../lib/router.js'
import { homeFor } from '../routes.js'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function LoginPage() {
  const { login } = useAuth()
  const [values, setValues] = useState({ email: '', password: '' })
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [loading, setLoading] = useState(false)

  const update = (name, value) => {
    setValues((v) => ({ ...v, [name]: value }))
    setErrors((e) => ({ ...e, [name]: '' }))
    setServerError('')
  }

  const validate = () => {
    const next = {}
    if (!EMAIL_RE.test(values.email.trim())) next.email = 'Enter a valid email'
    if (!values.password) next.password = 'Enter your password'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (e) => {
    e.preventDefault()
    if (loading || !validate()) return
    setLoading(true)
    try {
      const user = await login(values.email.trim(), values.password, remember)
      navigate(homeFor(user.role), { replace: true })
    } catch (err) {
      setServerError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-brand">
        <Logo />
        <p>AI-powered placement preparation for students.</p>
      </div>

      <div className="auth-card">
        <div className="auth-head">
          <div className="auth-logo">
            <Icon name="spark" size={23} />
          </div>
          <h1>Welcome back</h1>
          <p>Sign in to continue to {APP_NAME}.</p>
        </div>

        <form onSubmit={submit} noValidate>
          <ErrorBanner>{serverError}</ErrorBanner>

          <FormField label="College email" htmlFor="email" error={errors.email}>
            <input
              className={`input ${errors.email ? 'input-error' : ''}`}
              id="email"
              type="email"
              value={values.email}
              placeholder="you@college.edu"
              autoComplete="email"
              autoFocus
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? 'email-error' : undefined}
              onChange={(e) => update('email', e.target.value)}
            />
          </FormField>

          <FormField label="Password" htmlFor="password" error={errors.password}>
            <div className="password-input">
              <input
                className={`input ${errors.password ? 'input-error' : ''}`}
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={values.password}
                placeholder="Enter your password"
                autoComplete="current-password"
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'password-error' : undefined}
                onChange={(e) => update('password', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <Icon name={showPassword ? 'eyeOff' : 'eye'} size={17} />
              </button>
            </div>
          </FormField>

          <div className="auth-options">
            <label>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />{' '}
              Remember me
            </label>
          </div>

          <Button className="full-btn auth-submit" type="submit" loading={loading}>
            {loading ? 'Signing in...' : 'Login'}
          </Button>
        </form>

        <div className="auth-switch">
          New student?{' '}
          <button type="button" onClick={() => navigate('/register')}>
            Register
          </button>
        </div>
      </div>

      <p className="auth-footer">{APP_NAME} · Placement Cell</p>
    </div>
  )
}
