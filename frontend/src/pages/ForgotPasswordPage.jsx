import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '../components/ui';
import { ApplicationHeader } from '../components/MoodleLayout';
import { MOODLE_URL, USE_MOODLE_MOCK } from '../services/config';
import styles from './AuthPages.module.css';

export default function ForgotPasswordPage() {
  const [info, setInfo] = useState('');

  const handleSubmit = (event) => {
    if (!USE_MOODLE_MOCK) return;
    event.preventDefault();
    setInfo('Pemulihan kata sandi belum tersedia');
  };

  return (
    <div className="approved-app">
      <ApplicationHeader />
      <main className="approved-login">
        <div className={styles.loginWrapper}>
          <div className={styles.loginCard}>
            <div className={styles.brandPanel}>
              <div>
                <div className={styles.brandBadge}>AGENTIC LMS</div>
                <h1 className={styles.brandHeroTitle}>Pulihkan akses<br />akun Anda</h1>
              </div>
              <div className={styles.brandFooter}>Institut Teknologi Kalimantan</div>
            </div>
            <div className={styles.formPanel}>
              <h2 className={styles.formTitle}>Lupa kata sandi?</h2>
              <p className={styles.helperText}>
                Masukkan username atau alamat email yang terdaftar.
              </p>
              {info && <Alert tone="info">{info}</Alert>}
              <form
                method="post"
                action={`${MOODLE_URL}/login/forgot_password.php`}
                onSubmit={handleSubmit}
              >
                <div className={styles.formGroup}>
                  <label className={styles.formLabel} htmlFor="recovery-username">Username atau alamat email</label>
                  <input
                    id="recovery-username"
                    name="username"
                    className={styles.formInput}
                    autoComplete="username"
                    placeholder="Masukkan username atau email"
                    required
                  />
                </div>
                <div className={styles.buttonRow}>
                  <button type="submit" className={styles.btnPrimary}>Kirim instruksi pemulihan</button>
                </div>
              </form>
              <Link to="/login" className={styles.backToLogin}>Kembali ke halaman masuk</Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
