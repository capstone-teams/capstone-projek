import React, { useState } from 'react'
import type { AuthUser } from '../../types/auth'
import { useAuth } from '../../hooks/useAuth'
import { MOCK_USERS } from '../../services/authService'
import { GOOGLE_CLIENT_ID } from '../../services/googleIdentity'
import { GoogleSignInButton } from './components/GoogleSignInButton'
import styles from './LoginPage.module.css'

interface LoginPageProps {
  onLoginSuccess: (user: AuthUser) => void
}

type LoginMode = 'login' | 'forgot-password'

const GOOGLE_ACCOUNTS = Object.values(MOCK_USERS).map((user) => user.profile)

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const {
    login,
    loginWithGoogle,
    loginWithGoogleIdToken,
    requestPasswordReset,
    isSubmitting,
    error,
    clearError,
  } = useAuth()
  const usernameError = error?.field === 'username' ? error.message : null
  const passwordError = error?.field === 'password' ? error.message : null
  const formError = error && !error.field ? error.message : null

  const [mode, setMode] = useState<LoginMode>('login')
  const [username, setUsername] = useState('dosen')
  const [password, setPassword] = useState('password123')
  const [showPassword, setShowPassword] = useState(false)
  const [isGooglePickerOpen, setIsGooglePickerOpen] = useState(false)
  const [resetSentTo, setResetSentTo] = useState<string | null>(null)

  const switchMode = (next: LoginMode) => {
    clearError()
    setResetSentTo(null)
    setIsGooglePickerOpen(false)
    setMode(next)
  }

  const handleLogin = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    const user = await login({ username, password })
    if (user) onLoginSuccess(user)
  }

  const handleGoogleAccount = async (email: string) => {
    const user = await loginWithGoogle(email)
    if (user) onLoginSuccess(user)
  }

  const handleGoogleCredential = async (idToken: string) => {
    const user = await loginWithGoogleIdToken(idToken)
    if (user) onLoginSuccess(user)
  }

  const handlePasswordReset = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (await requestPasswordReset(username)) setResetSentTo(username.trim())
  }

  const usernameInput = (
    <div className={styles.formGroup}>
      <input
        id="login-username"
        type="text"
        className={`${styles.formInput} ${usernameError ? styles.formInputError : ''}`.trim()}
        aria-label="ID Number (username) / email"
        aria-invalid={usernameError ? true : undefined}
        aria-describedby={usernameError ? 'login-username-error' : undefined}
        value={username}
        onChange={(e) => {
          setUsername(e.target.value)
          if (error) clearError()
        }}
        placeholder="ID Number(username) / email"
        autoComplete="username"
        required
      />
      {usernameError && (
        <p id="login-username-error" className={styles.fieldError} role="alert">
          {usernameError}
        </p>
      )}
    </div>
  )

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
          {mode === 'login' ? (
            <>
              <h2 className={styles.formTitle}>Masuk ke akun Anda</h2>

              <form onSubmit={handleLogin}>
                {usernameInput}

                <div className={styles.formGroup}>
                  <div className={styles.passwordField}>
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      className={`${styles.formInput} ${passwordError ? styles.formInputError : ''}`.trim()}
                      aria-label="Password"
                      aria-invalid={passwordError ? true : undefined}
                      aria-describedby={passwordError ? 'login-password-error' : undefined}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value)
                        if (error) clearError()
                      }}
                      placeholder="Password"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      className={styles.passwordToggle}
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}
                      aria-pressed={showPassword}
                      aria-controls="login-password"
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                  {passwordError && (
                    <p id="login-password-error" className={styles.fieldError} role="alert">
                      {passwordError}
                    </p>
                  )}
                </div>

                <div className={styles.forgotRow}>
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => switchMode('forgot-password')}
                  >
                    Lupa kata sandi?
                  </button>
                </div>

                <div className={styles.buttonRow}>
                  <button
                    type="submit"
                    className={styles.btnPrimary}
                    style={{ width: '100%' }}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Memproses…' : 'Masuk'}
                  </button>
                </div>
              </form>

              <div className={styles.divider}>atau</div>

              {GOOGLE_CLIENT_ID ? (
                <GoogleSignInButton
                  clientId={GOOGLE_CLIENT_ID}
                  onCredential={handleGoogleCredential}
                />
              ) : isGooglePickerOpen ? (
                <div className={styles.accountPicker}>
                  <div className={styles.accountPickerHeader}>
                    <span className={styles.accountPickerTitle}>Pilih akun Google</span>
                    <button
                      type="button"
                      className={styles.linkButton}
                      onClick={() => {
                        clearError()
                        setIsGooglePickerOpen(false)
                      }}
                    >
                      Batal
                    </button>
                  </div>
                  <ul className={styles.accountList}>
                    {GOOGLE_ACCOUNTS.map((account) => (
                      <li key={account.email}>
                        <button
                          type="button"
                          className={styles.accountItem}
                          onClick={() => handleGoogleAccount(account.email)}
                          disabled={isSubmitting}
                        >
                          <span className={styles.accountAvatar} aria-hidden="true">
                            {account.avatarInitial}
                          </span>
                          <span className={styles.accountText}>
                            <span className={styles.accountName}>{account.name}</span>
                            <span className={styles.accountEmail}>{account.email}</span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <button
                  type="button"
                  className={styles.btnGoogle}
                  onClick={() => {
                    clearError()
                    setIsGooglePickerOpen(true)
                  }}
                >
                  <GoogleIcon />
                  <span>Masuk dengan Google</span>
                </button>
              )}

              {formError && (
                <p className={`${styles.fieldError} ${styles.socialError}`} role="alert">
                  {formError}
                </p>
              )}
            </>
          ) : (
            <>
              <h2 className={styles.formTitle}>Lupa kata sandi</h2>

              <form onSubmit={handlePasswordReset}>
                {resetSentTo ? (
                  <p className={styles.notice} role="status">
                    Jika akun <strong>{resetSentTo}</strong> terdaftar, tautan untuk mengatur ulang
                    kata sandi telah dikirim ke email ITK Anda.
                  </p>
                ) : (
                  <>
                    <p className={styles.helperText} style={{ marginTop: 0, marginBottom: 16 }}>
                      Masukkan username atau email ITK Anda. Kami akan mengirim tautan untuk
                      mengatur ulang kata sandi.
                    </p>
                    {usernameInput}
                    <div className={styles.buttonRow}>
                      <button
                        type="submit"
                        className={styles.btnPrimary}
                        style={{ width: '100%' }}
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? 'Mengirim…' : 'Kirim tautan reset'}
                      </button>
                    </div>
                  </>
                )}

                <div className={styles.backRow}>
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => switchMode('login')}
                  >
                    Kembali ke halaman masuk
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 19c-6.5 0-10-7-10-7a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 7 10 7a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="2" y1="2" x2="22" y2="22" />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  )
}
