// import { useState } from 'react';
// import { Navigate, useLocation, useNavigate } from 'react-router-dom';
// import { useAuth } from '../../hooks/useAuth';
// import { getDefaultPathForRole, isPathAllowedForRole } from '../../utils/navigation';
// import { USE_MOCK } from '../../services/config';
// import styles from './LoginPage.module.css';
// export const LoginPage = () => {
//     const [username, setUsername] = useState(USE_MOCK ? 'dosen' : '');
//     const [password, setPassword] = useState(USE_MOCK ? 'dosen123' : '');
//     const [errorMessage, setErrorMessage] = useState(null);
//     const { user, login } = useAuth();
//     const location = useLocation();
//     const navigate = useNavigate();
//     const [pending, setPending] = useState(false);
//     const requested = location.state?.from;
//     const destination = (role) => requested && isPathAllowedForRole(requested.pathname, role)
//         ? requested.pathname + (requested.search ?? '') : getDefaultPathForRole(role);
//     const handleLogin = async (event) => {
//         event.preventDefault();
//         setPending(true);
//         setErrorMessage(null);
//         try {
//             const next = await login(username, password);
//             navigate(destination(next.role), { replace: true });
//         } catch (error) { setErrorMessage(error.message); }
//         finally { setPending(false); }
//     };
//     if (user) return <Navigate to={destination(user.role)} replace />;
//     return (<div className={styles.loginWrapper}>
//       <div className={styles.loginCard}>
//         {/* Identitas / Left Blue Banner */}
//         <div className={styles.brandPanel}>
//           <div>
//             <div className={styles.brandBadge}>AGENTIC LMS</div>
//             <h1 className={styles.brandHeroTitle}>
//               Persiapan pembelajaran
//               <br />
//               berbasis RPS
//             </h1>
//           </div>
//           <div className={styles.brandFooter}>Institut Teknologi Kalimantan</div>
//         </div>
//
//         {/* Login Form / Right Panel */}
//         <div className={styles.formPanel}>
//           <h2 className={styles.formTitle}>Masuk ke akun Anda</h2>
//
//           <form onSubmit={handleLogin}>
//             <div className={styles.formGroup}>
//               <label className={styles.formLabel} htmlFor="login-username">Username</label>
//               <input id="login-username" type="text" className={styles.formInput} value={username} onChange={(e) => {
//             setUsername(e.target.value);
//             if (errorMessage)
//                 setErrorMessage(null);
//         }} autoComplete="username" placeholder={USE_MOCK ? "Ketik 'dosen' atau 'mahasiswa'" : 'Email akun aplikasi'} required/>
//             </div>
//
//             <div className={styles.formGroup}>
//               <label className={styles.formLabel} htmlFor="login-password">Kata sandi</label>
//               <input id="login-password" type="password" autoComplete="current-password" required className={styles.formInput} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••"/>
//             </div>
//
//             {errorMessage && (<div role="alert" style={{
//                 color: '#DC2626',
//                 fontSize: '13px',
//                 marginBottom: '12px',
//                 backgroundColor: '#FEF2F2',
//                 padding: '8px 12px',
//                 borderRadius: '6px',
//                 border: '1px solid #FECACA',
//             }}>
//                 {errorMessage}
//               </div>)}
//
//             <div className={styles.buttonRow}>
//               <button disabled={pending} type="submit" className={styles.btnPrimary} style={{ width: '100%' }}>
//                 Masuk
//               </button>
//             </div>
//
//             <p className={styles.helperText}>
//               {USE_MOCK ? <>Akun demo: <strong>dosen / dosen123</strong> atau <strong>mahasiswa / mahasiswa123</strong>.</> : 'Gunakan email dan kata sandi akun aplikasi Anda.'}
//             </p>
//           </form>
//         </div>
//       </div>
//     </div>);
// };
