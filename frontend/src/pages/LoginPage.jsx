import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Alert } from '../components/ui';
import { MOODLE_URL, USE_MOODLE_MOCK } from '../services/config';
import { SESSION_NOTICE } from '../types/auth';

import { ApplicationHeader } from '../components/MoodleLayout';
import styles from '../features/auth/LoginPage.module.css';

const MESSAGES = {
  invalidlogin: 'Username atau password salah. Silakan coba lagi.',
  enablewsdescription: 'Layanan web Moodle belum aktif. Hubungi admin situs.',
  servicenotavailable: 'Layanan web Moodle belum aktif. Hubungi admin situs.',
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
      setError(MESSAGES[err.code] ?? err.message);
      setPending(false);
    }
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
          <div className={styles.formGroup}><label className={styles.formLabel} htmlFor="username">Username</label>
            <input id="username" className={styles.formInput} value={form.username} onChange={update('username')} autoComplete="username" placeholder="Masukkan username Moodle" required autoFocus />
          </div>
          <div className={styles.formGroup}><label className={styles.formLabel} htmlFor="password">Kata sandi</label>
            <input id="password" className={styles.formInput} type={showPassword ? 'text' : 'password'} value={form.password} onChange={update('password')} autoComplete="current-password" required />
            <button type="button" className="text-sm text-primary text-left" onClick={() => setShowPassword((value) => !value)} aria-pressed={showPassword}>{showPassword ? 'Sembunyikan password' : 'Tampilkan password'}</button>
          </div>
          <div className="mb-4 text-sm">
            {USE_MOODLE_MOCK ? <button type="button" className="text-primary" onClick={() => setInfo('Untuk mengatur ulang password, hubungi admin situs atau bagian akademik.')}>Lupa password?</button> : <a href={MOODLE_URL + '/login/forgot_password.php'} target="_blank" rel="noreferrer">Lupa password?</a>}
          </div>
          <div className={styles.buttonRow}><button type="submit" className={styles.btnPrimary} disabled={pending}>{pending ? 'Memproses…' : 'Masuk'}</button></div>
          <p className={styles.helperText}>{USE_MOODLE_MOCK ? <>Akun demo: <strong>dosen / dosen123</strong> atau <strong>mahasiswa / mahasiswa123</strong>.</> : 'Gunakan username dan kata sandi Moodle Anda.'}</p>
        </form>
      </div>
    </div></div></main>
  </div>;
}
