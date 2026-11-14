import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

import Icon from './Icon.jsx'

const ToastContext = createContext(null)
const DURATION_MS = 2600

/** One toast at a time, bottom-right (Figma design). showToast(text, {tone: 'success' | 'error'}). */
export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timer = useRef()

  const showToast = useCallback((text, { tone = 'success' } = {}) => {
    clearTimeout(timer.current)
    setToast({ text, tone, id: Date.now() })
    timer.current = setTimeout(() => setToast(null), DURATION_MS)
  }, [])

  useEffect(() => () => clearTimeout(timer.current), [])

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      {toast && (
        <div className={`toast toast-${toast.tone}`} key={toast.id} role="status">
          <span>
            <Icon name={toast.tone === 'error' ? 'alert' : 'check'} size={16} />
          </span>
          {toast.text}
        </div>
      )}
    </ToastContext.Provider>
  )
}

// oxlint-disable-next-line react/only-export-components
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
