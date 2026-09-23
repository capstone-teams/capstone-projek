import React, { useState } from 'react'
import type { AppPath } from '../../types/navigation'
import type { UserRole } from '../../types/auth'
import styles from './LoginPage.module.css'

interface LoginPageProps {
  onNavigate: (path: AppPath) => void
  onRoleChange: (role: UserRole) => void
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate, onRoleChange }) => {
  const [email, setEmail] = useState('chandra.cahyo@itk.ac.id')
  const [password, setPassword] = useState('password123')

  const handleLoginDosen = (e: React.FormEvent) => {
    e.preventDefault()
    onRoleChange('dosen')
    onNavigate('/dashboard')
  }

  const handleLoginMahasiswa = () => {
    onRoleChange('mahasiswa')
    onNavigate('/student/courses')
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

          <form onSubmit={handleLoginDosen}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Email / username</label>
              <input
                type="text"
                className={styles.formInput}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nama@itk.ac.id"
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
                required
              />
            </div>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.btnPrimary}>
                Masuk sebagai Dosen
              </button>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleLoginMahasiswa}
              >
                Masuk Mahasiswa
              </button>
            </div>

            <p className={styles.helperText}>
              Gunakan akun institusi yang diberikan untuk sistem persiapan RPS.
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
