import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Alert } from '../../components/ui';
import { AuthField, AuthLayout, AuthSubmitButton, GoogleLoginButton, PasswordField } from '../../components/auth';
import { SESSION_NOTICE } from '../../types/auth';

const MESSAGES = {
  invalidlogin: 'Username atau password salah. Silakan coba lagi.',
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

  return (
    <AuthLayout heroTitle={<>Persiapan pembelajaran<br />berbasis RPS</>} title="Masuk ke akun Anda">
      {error && <Alert tone="danger" title="Login gagal">{error}</Alert>}
      {info && <Alert tone="info">{info}</Alert>}
      {!error && !info && sessionNotice === SESSION_NOTICE.EXPIRED && <Alert tone="info" title="Sesi berakhir">Sesi Anda telah berakhir. Silakan masuk kembali.</Alert>}
      <form onSubmit={onSubmit}>
        <AuthField id="username" label="Username" value={form.username} onChange={update('username')} autoComplete="username" placeholder="ID Number (username) / email" required autoFocus />
        <PasswordField id="password" label="Kata sandi" value={form.password} onChange={update('password')} autoComplete="current-password" placeholder="Password" required />
        <div className="mb-4 text-sm">
          <Link to="/forgot-password">Lupa password?</Link>
        </div>
        <AuthSubmitButton disabled={pending}>{pending ? 'Memproses…' : 'Masuk'}</AuthSubmitButton>
        <GoogleLoginButton onClick={onGoogleLogin} />
      </form>
    </AuthLayout>
  );
}
