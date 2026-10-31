import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '../../components/ui';
import { AuthField, AuthLayout, AuthSubmitButton } from '../../components/auth';

export default function ForgotPasswordPage() {
  const [info, setInfo] = useState('');

  // Backend belum menyediakan endpoint pemulihan kata sandi; formulir tidak dikirim ke Moodle.
  const handleSubmit = (event) => {
    event.preventDefault();
    setInfo('Pemulihan kata sandi belum tersedia');
  };

  return (
    <AuthLayout heroTitle={<>Pulihkan akses<br />akun Anda</>} title="Lupa kata sandi?">
      <p className="mt-3 text-[13px] text-muted">
        Masukkan username atau alamat email yang terdaftar.
      </p>
      {info && <Alert tone="info">{info}</Alert>}
      <form onSubmit={handleSubmit}>
        <AuthField
          id="recovery-username"
          name="username"
          label="Username atau alamat email"
          autoComplete="username"
          placeholder="Masukkan username atau email"
          required
        />
        <AuthSubmitButton>Kirim instruksi pemulihan</AuthSubmitButton>
      </form>
      <Link to="/login" className="mt-5 inline-block text-[13px] font-semibold text-primary no-underline hover:underline">
        Kembali ke halaman masuk
      </Link>
    </AuthLayout>
  );
}
