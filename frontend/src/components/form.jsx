// Form widgets from the Figma design (profile page, later drives). Styles in styles/global.css.
import { useState } from 'react'

import Icon from './Icon.jsx'

/**
 * Labelled field. `missing` adds the amber "Not filled" marker; `error` replaces the hint.
 * `id` goes on the wrapper so the completeness card can scroll to it.
 */
export function Field({ label, htmlFor, id, hint, error, missing = false, className = '', children }) {
  const message = error || (missing ? (hint ? `Not filled · ${hint}` : 'Not filled') : hint)
  return (
    <div className={`field ${missing ? 'field-missing' : ''} ${className}`} id={id}>
      <label className="field-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? (
        <span className="validation-error" id={`${htmlFor}-error`}>
          {error}
        </span>
      ) : (
        message && <small>{message}</small>
      )}
    </div>
  )
}

/**
 * Chips + text input. Enter or comma adds, Backspace on an empty input removes the last chip,
 * blur adds whatever is typed (so a half-typed skill isn't lost on Save).
 * Duplicates are ignored case-insensitively, like the backend.
 */
export function TagEditor({ id, tags, onChange, placeholder, max = 30, maxLength = 50 }) {
  const [value, setValue] = useState('')
  const full = tags.length >= max

  const add = () => {
    const tag = value.replace(/\s+/g, ' ').trim()
    setValue('')
    if (!tag || full) return
    if (tags.some((t) => t.toLowerCase() === tag.toLowerCase())) return
    onChange([...tags, tag])
  }

  return (
    <div className="tag-editor">
      {tags.map((tag) => (
        <span className="chip" key={tag}>
          {tag}
          <button type="button" aria-label={`Remove ${tag}`} onClick={() => onChange(tags.filter((t) => t !== tag))}>
            <Icon name="close" size={12} />
          </button>
        </span>
      ))}
      <input
        id={id}
        value={value}
        maxLength={maxLength}
        disabled={full}
        placeholder={full ? `Maximum ${max} reached` : tags.length ? '' : placeholder}
        onChange={(e) => setValue(e.target.value)}
        onBlur={add}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault()
            add()
          } else if (e.key === 'Backspace' && !value && tags.length) {
            onChange(tags.slice(0, -1))
          }
        }}
      />
    </div>
  )
}

/** "+ Java" buttons under a TagEditor for suggestions not already added. */
export function Suggestions({ options, tags, onAdd }) {
  const have = new Set(tags.map((t) => t.toLowerCase()))
  const left = options.filter((o) => !have.has(o.toLowerCase()))
  if (!left.length) return null
  return (
    <div className="suggestion-row">
      <span>Suggested:</span>
      {left.map((option) => (
        <button type="button" key={option} onClick={() => onAdd(option)}>
          + {option}
        </button>
      ))}
    </div>
  )
}

/** − [n] + counter for whole numbers between 0 and max. */
export function NumberStepper({ id, label, value, onChange, max = 99, compact = false }) {
  const clamp = (n) => Math.min(max, Math.max(0, Number.isFinite(n) ? Math.trunc(n) : 0))
  return (
    <div className={`stepper-field${compact ? 'compact-stepper' : ''}`}>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <span className="number-stepper">
        <button
          type="button"
          aria-label={`Decrease ${label}`}
          onClick={() => onChange(clamp(value - 1))}
          disabled={value <= 0}
        >
          −
        </button>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min="0"
          max={max}
          value={value}
          onChange={(e) => onChange(clamp(Number(e.target.value)))}
        />
        <button
          type="button"
          aria-label={`Increase ${label}`}
          onClick={() => onChange(clamp(value + 1))}
          disabled={value >= max}
        >
          +
        </button>
      </span>
    </div>
  )
}
