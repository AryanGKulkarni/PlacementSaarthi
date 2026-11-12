// Small building blocks from the Figma design. Styles live in styles/global.css.
import { APP_NAME } from '../lib/constants.js'
import Icon from './Icon.jsx'

export function Logo({ compact = false }) {
  return (
    <div className="logo-wrap">
      <div className="logo-mark">
        <Icon name="spark" size={20} />
      </div>
      {!compact && <span>{APP_NAME}</span>}
    </div>
  )
}

export function Button({
  children,
  variant = 'primary',
  icon,
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  return (
    <button className={`btn btn-${variant} ${className}`} disabled={loading || disabled} {...props}>
      {loading ? (
        <span className="button-spinner" aria-hidden="true" />
      ) : (
        icon && <Icon name={icon} size={17} />
      )}
      <span>{children}</span>
    </button>
  )
}

export function Badge({ children, tone = 'neutral' }) {
  return (
    <span className={`badge badge-${tone}`}>
      {tone === 'green' && <span className="badge-dot" />}
      {children}
    </span>
  )
}

/** Form field with label, required star, and an error or hint line under the input. */
export function FormField({ label, htmlFor, error, hint, required, children }) {
  return (
    <div className="field auth-field">
      <label className="field-label" htmlFor={htmlFor}>
        {label} {required && <span aria-hidden="true">*</span>}
      </label>
      {children}
      <div className="field-message">
        {error ? (
          <span className="validation-error" id={`${htmlFor}-error`}>
            {error}
          </span>
        ) : hint ? (
          <small>{hint}</small>
        ) : null}
      </div>
    </div>
  )
}

export function ErrorBanner({ children }) {
  if (!children) return null
  return (
    <div className="auth-error-banner" role="alert">
      <Icon name="alert" size={18} />
      <span>{children}</span>
    </div>
  )
}
