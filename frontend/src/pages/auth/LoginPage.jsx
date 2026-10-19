import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Alert } from '../../components/ui';
import { AuthField, AuthLayout, AuthSubmitButton, GoogleLoginButton, PasswordField } from '../../components/auth';
import { SESSION_NOTICE } from '../../types/auth';

// Pesan untuk kegagalan langkah Moodle (setelah akun backend terverifikasi).
const MOODLE_MESSAGES = {
  invalidlogin: 'Akun backend valid, tetapi Moodle menolak kredensial yang sama. Pastikan akun Moodle memakai username dan password yang sama.',
  enablewsdescription: 'Layanan web Moodle belum aktif.',
  servicenotavailable: 'Layanan web Moodle belum aktif.',
  networkerror: 'Tidak dapat terhubung ke server Moodle. Coba beberapa saat lagi.',
};

/** Error backend ditampilkan apa adanya (error.message dari kontrak §18); error Moodle diberi konteks. */
function describeLoginError(err) {
  if (err?.source === 'moodle') {
    return { title: 'Login Moodle gagal', message: MOODLE_MESSAGES[String(err.code ?? '').toLowerCase()] ?? err.message ?? 'Login Moodle gagal.' };
  }
  return { title: 'Login gagal', message: err?.message || 'Login gagal. Silakan coba lagi.' };
}

export default function LoginPage() {
  const { user, login, sessionNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState('');

  if (user) return <Navigate to="/my" replace />;

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    setInfo('');
    try {
      await login(form.username.trim(), form.password);
      navigate(location.state?.from?.pathname || '/my', { replace: true });
    } catch (err) {
      if (err?.name !== 'AbortError') setError(describeLoginError(err));
      setPending(false);
    }
  };

  const onGoogleLogin = () => {
    setError(null);
    setInfo('Login menggunakan Google belum tersedia. Hubungi admin untuk mengaktifkan integrasi Google OAuth.');
  };

  return (
    <AuthLayout heroTitle={<>Persiapan pembelajaran<br />berbasis RPS</>} title="Masuk ke akun Anda">
      {error && <Alert tone="danger" title={error.title}>{error.message}</Alert>}
      {info && <Alert tone="info">{info}</Alert>}
      {!error && !info && sessionNotice === SESSION_NOTICE.EXPIRED && <Alert tone="info" title="Sesi berakhir">Sesi Anda telah berakhir. Silakan masuk kembali.</Alert>}
      {!error && !info && sessionNotice === SESSION_NOTICE.UNAVAILABLE && (
        <Alert tone="warning" title="Sesi belum dapat dipulihkan">Server tidak dapat dihubungi. Muat ulang halaman nanti, atau masuk kembali.</Alert>
      )}
      <form onSubmit={onSubmit} aria-busy={pending}>
        <AuthField id="username" label="Username" value={form.username} onChange={update('username')} autoComplete="username" placeholder="ID Number (username) / email" required autoFocus readOnly={pending} />
        <PasswordField id="password" label="Kata sandi" value={form.password} onChange={update('password')} autoComplete="current-password" placeholder="Password" required readOnly={pending} />
        <div className="mb-4 text-sm">
          <Link to="/forgot-password">Lupa password?</Link>
        </div>
        <AuthSubmitButton disabled={pending}>{pending ? 'Memproses…' : 'Masuk'}</AuthSubmitButton>
        <GoogleLoginButton onClick={onGoogleLogin} />
      </form>
    </AuthLayout>
  );
}
