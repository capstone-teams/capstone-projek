import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { MOODLE_URL } from '../services/config';
import styles from './layout/AppNavbar.module.css';

function UserMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const location = useLocation();
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) { setLastPath(location.pathname); setOpen(false); }
  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => !ref.current?.contains(event.target) && setOpen(false);
    const escape = (event) => event.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', escape); };
  }, [open]);
  const initials = user.fullname.split(' ').map((name) => name[0]).slice(0, 2).join('');
  const item = styles.dropdownItem;
  return <div className={styles.userMenuContainer} ref={ref}>
    <button type="button" className={styles.userPill} aria-label="Menu pengguna" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span className={styles.avatarBadge}>{initials}</span><span className={styles.userName}>{user.fullname}</span><span className="sr-only">{user.role === 'dosen' ? 'Dosen' : 'Mahasiswa'}</span><span aria-hidden="true" className={styles.dropdownArrow}>▾</span>
    </button>
    {open && <div role="menu" className={styles.dropdownMenu}>
      <div className={styles.dropdownSection}>{user.role === 'dosen' ? 'Dosen' : 'Mahasiswa'}</div>
      <Link role="menuitem" to="/my" className={item}>Dasbor</Link>
      <Link role="menuitem" to="/my/courses" className={item}>Kursus saya</Link>
      <Link role="menuitem" to="/user/profile" className={item}>Profil</Link>
      {user.role === 'dosen' && <Link role="menuitem" to="/ai" className={item}>Generator AI</Link>}
      <a role="menuitem" href={MOODLE_URL} target="_blank" rel="noreferrer" className={item}>Buka Moodle asli ↗</a>
      <div className={styles.dropdownDivider} />
      <button type="button" role="menuitem" className={item} onClick={onLogout}>Keluar</button>
    </div>}
  </div>;
}

export function ApplicationHeader() {
  const { user, logout } = useAuth();
  return <header className={styles.header}><div className={styles.headerInner}>
    <Link to={user ? '/my' : '/login'} className={styles.brand}>
      <span className={styles.brandLogo}>ITK</span><span className={styles.brandTitle}>Agentic LMS</span><span className={styles.brandSubtitle}>· Institut Teknologi Kalimantan</span>
    </Link>
    {user ? <UserMenu user={user} onLogout={logout} /> : <Link to="/login">Masuk</Link>}
  </div></header>;
}

export default function MoodleLayout() {
  return <div className="approved-app"><ApplicationHeader /><Outlet /></div>;
}

export function PageContainer({ children }) {
  return <main className="approved-page">{children}</main>;
}
