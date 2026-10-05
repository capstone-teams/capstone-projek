import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Alert } from '../components/ui';
import { USE_MOODLE_MOCK } from '../services/config';
import { SESSION_NOTICE } from '../types/auth';

import { ApplicationHeader } from '../components/MoodleLayout';
import styles from '../features/auth/LoginPage.module.css';

const MESSAGES = {
  invalidlogin: 'login tidak valid. Silakan coba lagi.',
  authentication_failed: 'Username atau password salah. Silakan coba lagi.',
  enablewsdescription: 'Layanan web Moodle belum aktif.',
  servicenotavailable: 'Layanan web Moodle belum aktif.',
  networkerror: 'Tidak dapat terhubung ke server. Coba beberapa saat lagi.',
};

export default function LoginPage() {
  const { user, login, sessionNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  if (user) return <Navigate to="/my" replace />;

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setPending(true);
    setError('');
    setInfo('');
    try {
      await login(form.username.trim(), form.password);
      navigate(location.state?.from?.pathname || '/my', { replace: true });
    } catch (err) {
      const errorCode = String(err?.code ?? '').toLowerCase();
      const errorMessage = String(err?.message ?? '');
      const isInvalidCredentials = /invalid login|username atau password salah|authentication failed/i.test(errorMessage);
      setError(MESSAGES[errorCode] ?? (isInvalidCredentials
        ? MESSAGES.invalidlogin
        : errorMessage || 'Login gagal. Silakan coba lagi.'));
      setPending(false);
    }
  };

  const onGoogleLogin = () => {
    setError('');
    setInfo('Login menggunakan Google belum tersedia. Hubungi admin untuk mengaktifkan integrasi Google OAuth.');
  };

  return <div className="approved-app">
    <ApplicationHeader />
    <main className="approved-login"><div className={styles.loginWrapper}><div className={styles.loginCard}>
      <div className={styles.brandPanel}>
        <div><div className={styles.brandBadge}>AGENTIC LMS</div><h1 className={styles.brandHeroTitle}>Persiapan pembelajaran<br />berbasis RPS</h1></div>
        <div className={styles.brandFooter}>Institut Teknologi Kalimantan</div>
      </div>
      <div className={styles.formPanel}>
        <h2 className={styles.formTitle}>Masuk ke akun Anda</h2>
        {error && <Alert tone="danger" title="Login gagal">{error}</Alert>}
        {info && <Alert tone="info">{info}</Alert>}
        {!error && !info && sessionNotice === SESSION_NOTICE.EXPIRED && <Alert tone="info" title="Sesi berakhir">Sesi Anda telah berakhir. Silakan masuk kembali.</Alert>}
      <form onSubmit={onSubmit}>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel} htmlFor="username">Username</label>
                  <input id="username" className={styles.formInput} value={form.username} onChange={update('username')} autoComplete="username" placeholder="Masukkan username Moodle" required autoFocus />
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel} htmlFor="password">Kata sandi</label>
                  <div className={styles.passwordInputWrapper}>
                    <input id="password" className={styles.formInput} type={showPassword ? 'text' : 'password'} value={form.password} onChange={update('password')} autoComplete="current-password" required />
                    {/* Mengganti Emoji dengan SVG Icon */}
                    <button type="button" className={styles.passwordToggle} onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'} aria-pressed={showPassword} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '0 8px', color: '#6b7280' }}>
                      {showPassword ? (
                        // Ikon Mata Dicoret (Hide Password)
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"></path>
                          <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"></path>
                          <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"></path>
                          <line x1="1" y1="1" x2="23" y2="23"></line>
                        </svg>
                      ) : (
                        // Ikon Mata Terbuka (Show Password)
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                          <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                      )}
                    </button>
            </div>
          </div>
          <div className="mb-4 text-sm">
            <Link to="/forgot-password">Lupa password?</Link>
          </div>
          <div className={styles.buttonRow}><button type="submit" className={styles.btnPrimary} disabled={pending}>{pending ? 'Memproses…' : 'Masuk'}</button></div>
          <div className={styles.separator}><span>atau</span></div>
          <button type="button" className={styles.googleButton} onClick={onGoogleLogin}>
            <svg className={styles.googleIcon} viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M23.49 12.27c0-.78-.07-1.53-.2-2.27H12v4.51h6.44a5.5 5.5 0 0 1-2.39 3.61v3h3.87c2.27-2.09 3.57-5.17 3.57-8.85Z" />
              <path fill="#34A853" d="M12 24c3.24 0 5.96-1.08 7.95-2.92l-3.87-3c-1.08.72-2.46 1.15-4.08 1.15-3.14 0-5.8-2.12-6.75-4.97H1.25v3.09A12 12 0 0 0 12 24Z" />
              <path fill="#FBBC05" d="M5.25 14.26a7.2 7.2 0 0 1 0-4.52V6.65H1.25a12 12 0 0 0 0 10.7l4-3.09Z" />
              <path fill="#EA4335" d="M12 4.77c1.77 0 3.35.61 4.6 1.8l3.45-3.45C17.95 1.16 15.24 0 12 0A12 12 0 0 0 1.25 6.65l4 3.09C6.2 6.89 8.86 4.77 12 4.77Z" />
            </svg>
            Lanjutkan dengan Google
          </button>
        </form>
      </div>
    </div></div></main>
  </div>;
}
