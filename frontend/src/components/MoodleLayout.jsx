import { useEffect, useRef, useState } from 'react';
<<<<<<< HEAD
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { MOODLE_URL } from '../services/config';
import { Avatar, Badge } from './ui';

const ROLE_LABEL = { dosen: 'Dosen', mahasiswa: 'Mahasiswa' };

function primaryNav(role) {
  const items = [
    { to: '/my', label: 'Dasbor' },
    { to: '/my/courses', label: 'Kursus saya' },
  ];
  if (role === 'dosen') items.push({ to: '/ai', label: 'Generator AI' });
  return items;
}
=======
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { MOODLE_URL } from '../services/config';
import AppStatus from './AppStatus';
import styles from './layout/AppNavbar.module.css';
>>>>>>> origin/develop

function UserMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const location = useLocation();
  const [lastPath, setLastPath] = useState(location.pathname);
<<<<<<< HEAD
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => !ref.current?.contains(e.target) && setOpen(false);
    const esc = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);

  const item = 'block px-4 py-2 text-ink no-underline hover:bg-primary hover:text-white';
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 hover:bg-surface"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Avatar name={user.fullname} src={user.avatar} />
        <span className="text-muted" aria-hidden="true">
          ▾
        </span>
        <span className="sr-only">Menu pengguna</span>
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-40 mt-1 w-60 rounded-md border border-line bg-white py-1.5 shadow-lg">
          <div className="border-b border-line px-4 pb-2 mb-1">
            <div className="font-semibold">{user.fullname}</div>
            <div className="text-sm text-muted">{ROLE_LABEL[user.role]}</div>
          </div>
          <Link role="menuitem" to="/user/profile" className={item}>
            Profil
          </Link>
          <Link role="menuitem" to="/my/courses" className={item}>
            Kursus saya
          </Link>
          <a role="menuitem" href={MOODLE_URL} target="_blank" rel="noreferrer" className={item}>
            Buka Moodle asli ↗
          </a>
          <div className="my-1 border-t border-line" />
          <button type="button" role="menuitem" onClick={onLogout} className={`${item} w-full cursor-pointer text-left`}>
            Keluar
          </button>
        </div>
      )}
    </div>
  );
}

export default function MoodleLayout() {
  const { user, site, logout } = useAuth();
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const nav = primaryNav(user.role);
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setDrawer(false);
  }

  // Gaya .mds-nav-pill Moodle 5.3: pill abu saat terpilih + titik indikator biru.
  const pillClass = ({ isActive }) =>
    `inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium no-underline ${
      isActive ? 'bg-line-subtle text-ink hover:text-ink' : 'text-ink-subtle hover:bg-line-subtle hover:text-ink-subtle active:bg-line'
    }`;

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-30 h-[61px] border-b border-line bg-surface">
        <div className="flex h-full items-center gap-2 px-4">
          <button
            type="button"
            className="grid size-9 cursor-pointer place-items-center rounded-md text-xl hover:bg-surface md:hidden"
            aria-label="Buka navigasi"
            aria-expanded={drawer}
            onClick={() => setDrawer((v) => !v)}
          >
            ☰
          </button>
          {/* Seperti Moodle tanpa logo situs: navbar menampilkan nama situs. */}
          <Link to="/my" className="mr-3 max-w-56 truncate text-lg font-bold text-ink no-underline hover:text-ink">
            {site?.name ?? 'Moodle'}
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Navigasi utama">
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/my'} className={pillClass}>
                {({ isActive }) => (
                  <>
                    <span>{n.label}</span>
                    {isActive && <span className="size-1 rounded-full bg-primary" aria-hidden="true" />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="flex-1" />
          <Badge tone={user.role === 'dosen' ? 'info' : 'success'}>{ROLE_LABEL[user.role]}</Badge>
          <UserMenu user={user} onLogout={logout} />
        </div>
      </header>

      {drawer && (
        <div className="fixed inset-0 top-[61px] z-20 bg-black/30 md:hidden" onClick={() => setDrawer(false)}>
          <nav className="h-full w-72 bg-white py-2 shadow-lg" aria-label="Navigasi utama" onClick={(e) => e.stopPropagation()}>
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === '/my'}
                className={({ isActive }) =>
                  `block border-l-4 px-4 py-2.5 text-ink no-underline ${isActive ? 'border-primary bg-primary-light' : 'border-transparent'}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      )}

      <Outlet />

      <footer className="mt-10 border-t border-line bg-surface px-4 py-6 text-center text-sm text-muted">
        {site?.name}
      </footer>
    </div>
  );
}

/** Wadah konten halaman dengan lebar maksimum ala Moodle. */
export function PageContainer({ children, wide = false }) {
  return <main className={`mx-auto w-full px-4 py-6 md:px-8 ${wide ? 'max-w-[1400px]' : 'max-w-[1200px]'}`}>{children}</main>;
=======
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
    {user && <UserMenu user={user} onLogout={logout} />}
  </div></header>;
}

export default function MoodleLayout() {
  return <div className="approved-app"><ApplicationHeader /><AppStatus /><Outlet /></div>;
}

export function PageContainer({ children }) {
  return <main className="approved-page">{children}</main>;
>>>>>>> origin/develop
}
