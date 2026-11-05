import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Alert } from '../../components/ui';
import { AuthField, AuthLayout, AuthSubmitButton, GoogleLoginButton, PasswordField } from '../../components/auth';
import { SESSION_NOTICE, homePathFor } from '../../types/auth';
import { MSG_LOGIN_FAILED, logTechnical } from '../../utils/userMessages';

// Kegagalan di belakang layar (layanan kursus) tidak disebut ke pengguna; detailnya hanya ke konsol.
const ACCOUNT_NOT_READY = 'Akun Anda belum dapat digunakan untuk masuk. Hubungi admin.';
const WRONG_CREDENTIALS = 'Username atau kata sandi salah. Periksa username, lalu ketik ulang kata sandi Anda.';
const SERVICE_DOWN_CODES = ['networkerror', 'invalidresponse', 'enablewsdescription', 'servicenotavailable'];

// Spasi, baris baru, NBSP, dan karakter lebar-nol di tepi password biasanya terbawa dari salin-tempel dan
// tidak terlihat di kolom, tetapi membuat backend menolak password yang tampak benar.
const EDGE_NOISE = /^[\s\u200b-\u200d\u2060\ufeff]+|[\s\u200b-\u200d\u2060\ufeff]+$/g;

/** Pesan backend yang sudah ramah (kontrak §18) ditampilkan apa adanya; sisanya dibuat umum. */
function describeLoginError(err) {
  if (err?.source === 'moodle') {
    logTechnical('login', { code: err.code, message: err.message });
    const code = String(err.code ?? '').toLowerCase();
    return { title: 'Login gagal', message: SERVICE_DOWN_CODES.includes(code) ? err.message : ACCOUNT_NOT_READY };
  }
  if (err?.status === 401) return { title: 'Login gagal', message: WRONG_CREDENTIALS };
  return { title: 'Login gagal', message: err?.message || MSG_LOGIN_FAILED };
}

export default function LoginPage() {
  const { user, login, sessionNotice } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState('');

  // Setelah login: dosen ke dashboard, mahasiswa ke halaman course (role dari GET /auth/me).
  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    setInfo('');
    try {
      const username = form.username.trim();
      let session;
      try {
        session = await login(username, form.password);
      } catch (err) {
        // Ditolak: coba sekali lagi tanpa karakter tak terlihat di tepi password, bila ada.
        const cleaned = form.password.replace(EDGE_NOISE, '');
        if (err?.status !== 401 || cleaned === form.password) throw err;
        logTechnical('login', { retry: 'password dibersihkan dari karakter tak terlihat di tepi', panjangAsli: form.password.length, panjangBersih: cleaned.length });
        session = await login(username, cleaned);
      }
      navigate(homePathFor(session.user.role), { replace: true });
    } catch (err) {
      if (err?.status === 401) logTechnical('login', { ditolak: 401, panjangPassword: form.password.length, usernameKosongAtauSpasi: !form.username.trim() });
      if (err?.name !== 'AbortError') setError(describeLoginError(err));
      // Kata sandi yang ditolak dikosongkan agar tidak terkirim lagi (mis. hasil isian otomatis browser).
      if (err?.status === 401) setForm((f) => ({ ...f, password: '' }));
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
