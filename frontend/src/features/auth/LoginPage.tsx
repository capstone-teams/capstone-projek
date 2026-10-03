import React, { useState } from 'react'
import type { AppPath } from '../../types/navigation'
import type { UserRole } from '../../types/auth'
import styles from './LoginPage.module.css'

interface LoginPageProps {
  onNavigate: (path: AppPath) => void
  onRoleChange: (role: UserRole) => void
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate, onRoleChange }) => {
  const [username, setUsername] = useState('dosen')
  const [password, setPassword] = useState('password123')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanUsername = username.trim().toLowerCase()

    if (cleanUsername.includes('mahasiswa')) {
      setErrorMessage(null)
      onRoleChange('mahasiswa')
      onNavigate('/student/courses')
    } else if (cleanUsername.includes('dosen')) {
      setErrorMessage(null)
      onRoleChange('dosen')
      onNavigate('/dashboard')
    } else {
      setErrorMessage('Username harus berupa "dosen" atau "mahasiswa".')
    }
  }

  return (
    <div className={styles.loginWrapper}>
      <div className={styles.loginCard}>
        {/* Identitas / Left Blue Banner */}
        <div className={styles.brandPanel}>
          <div>
            <div className={styles.brandBadge}>AGENTIC LMS</div>
            <h1 className={styles.brandHeroTitle}>
              Persiapan pembelajaran
              <br />
              berbasis RPS
            </h1>
          </div>
          <div className={styles.brandFooter}>Institut Teknologi Kalimantan</div>
        </div>

        {/* Login Form / Right Panel */}
        <div className={styles.formPanel}>
          <h2 className={styles.formTitle}>Masuk ke akun Anda</h2>

          <form onSubmit={handleLogin}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Username</label>
              <input
                type="text"
                className={styles.formInput}
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value)
                  if (errorMessage) setErrorMessage(null)
                }}
                placeholder="Ketik 'dosen' atau 'mahasiswa'"
                required
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Kata sandi</label>
              <input
                type="password"
                className={styles.formInput}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
              />
            </div>

            {errorMessage && (
              <div
                style={{
                  color: '#DC2626',
                  fontSize: '13px',
                  marginBottom: '12px',
                  backgroundColor: '#FEF2F2',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid #FECACA',
                }}
              >
                {errorMessage}
              </div>
            )}

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.btnPrimary} style={{ width: '100%' }}>
                Masuk
              </button>
            </div>

            <p className={styles.helperText}>
              Ketik <strong>dosen</strong> untuk masuk ke akun dosen, atau <strong>mahasiswa</strong> untuk akun mahasiswa. Kata sandi tidak divalidasi.
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
