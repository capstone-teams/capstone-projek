import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider } from './features/auth/AuthProvider'
import './styles/global.css'

const root = document.getElementById('root')

if (!root) {
  throw new Error('Elemen root aplikasi tidak ditemukan.')
}

createRoot(root).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
