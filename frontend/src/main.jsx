import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import { ToastProvider } from './components/Toast.jsx'
import './styles/global.css'
import './styles/app.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </AuthProvider>
  </StrictMode>,
)
