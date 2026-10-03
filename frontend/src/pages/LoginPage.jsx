import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Alert } from '../components/ui';
import { MOODLE_URL, USE_MOODLE_MOCK } from '../services/config';

const SITE_NAME = 'Moodle ITK';

const MESSAGES = {
  invalidlogin: 'Username atau password salah. Silakan coba lagi.',
  enablewsdescription: 'Layanan web Moodle belum aktif. Hubungi admin situs.',
  servicenotavailable: 'Layanan web Moodle belum aktif. Hubungi admin situs.',
  networkerror: 'Tidak dapat terhubung ke server. Coba beberapa saat lagi.',
};

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function EyeIcon({ off }) {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {off && <path d="M3 3l18 18" />}
    </svg>
  );
}

// Input login Moodle 5.3 (.login-input-wrapper): ikon di kiri, latar gray-100, padding kiri 3rem.
const INPUT =
  '!rounded-lg !border-line !bg-surface !py-2.5 !ps-12 focus:!border-[#87b6df] focus:!ring-4 focus:!ring-primary/75';

/** Halaman login, meniru core/login_layout + core/loginform Moodle 5.3. */
export default function LoginPage() {
  const { user, login } = useAuth();
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

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      {/* .login-layout-left: panel biru dengan kotak sambutan (disembunyikan di layar kecil). */}
      <aside className="sticky top-0 hidden h-screen items-center justify-center bg-primary p-12 lg:flex">
        <div className="mb-20 max-w-[450px] rounded-lg bg-[rgba(6,41,73,0.65)] p-4 text-center text-white">
          <h2 className="mb-3 text-[2rem] font-bold">Selamat datang di {SITE_NAME}</h2>
          <p className="mb-4 text-left">
            Learning Management System Institut Teknologi Kalimantan. Akses materi perkuliahan, kumpulkan tugas, dan pantau nilai Anda di
            satu tempat.
          </p>
          <p>Gunakan akun yang diberikan oleh kampus untuk masuk.</p>
        </div>
      </aside>

      {/* .login-layout-right */}
      <main className="flex min-h-screen justify-center p-6 sm:p-12">
        <div className="my-auto w-full max-w-[576px]">
          <h1 className="text-[calc(1.325rem+0.9vw)] font-bold xl:text-[2rem]">Selamat datang kembali</h1>
          <p className="mb-6 text-muted">Log in ke {SITE_NAME}</p>

          {error && (
            <Alert tone="danger" title="Login gagal">
              {error}
            </Alert>
          )}
          {info && <Alert tone="info">{info}</Alert>}

          <form onSubmit={onSubmit}>
            <div className="mb-4">
              <label htmlFor="username" className="mb-2 block">
                Username
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted">
                  <UserIcon />
                </span>
                <input
                  id="username"
                  className={INPUT}
                  placeholder="Masukkan username"
                  value={form.username}
                  onChange={update('username')}
                  autoComplete="username"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="password" className="mb-2 block">
                Password
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted">
                  <LockIcon />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className={`${INPUT} !pe-12`}
                  placeholder="Masukkan password"
                  value={form.password}
                  onChange={update('password')}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="absolute end-2 top-1/2 grid size-8 -translate-y-1/2 cursor-pointer place-items-center rounded-md text-muted hover:text-ink"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'}
                  aria-pressed={showPassword}
                >
                  <EyeIcon off={showPassword} />
                </button>
              </div>
            </div>

            <div className="mb-4 text-end">
              {USE_MOODLE_MOCK ? (
                <button
                  type="button"
                  className="cursor-pointer text-primary hover:text-primary-dark hover:underline"
                  onClick={() => setInfo('Untuk mengatur ulang password, hubungi admin situs atau bagian akademik.')}
                >
                  Lupa password?
                </button>
              ) : (
                <a href={`${MOODLE_URL}/login/forgot_password.php`} target="_blank" rel="noreferrer">
                  Lupa password?
                </a>
              )}
            </div>

            <button type="submit" className="btn btn--primary w-full py-2.5" disabled={pending}>
              {pending ? 'Memproses…' : 'Log in'}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
