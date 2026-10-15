import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const ITEM_CLASS =
  'flex w-full cursor-pointer items-center justify-between border-none bg-transparent px-4 py-2 text-left text-[13px] text-ink transition-colors duration-[120ms] ease-[ease] hover:bg-line-subtle hover:text-ink max-tablet:min-h-10 max-tablet:py-2.5';

/** Tombol nama user di header beserta dropdown navigasi akun. */
export default function UserMenu({ user, onLogout }) {
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
  const roleLabel = user.role === 'dosen' ? 'Dosen' : 'Mahasiswa';
  return <div className="relative" ref={ref}>
    <button type="button" className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-line bg-white px-3.5 py-1.5 text-[13px] font-semibold text-ink transition-all duration-150 ease-[ease] hover:border-[#CBD5E1] hover:bg-surface max-tablet:gap-1 max-tablet:px-2 max-tablet:py-1" aria-label="Menu pengguna" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span className="flex size-[26px] items-center justify-center rounded-full bg-[#EFF6FF] text-[11px] font-bold text-primary">{initials}</span>
      <span className="max-w-[160px] truncate max-tablet:hidden">{user.fullname}</span>
      <span className="sr-only">{roleLabel}</span>
      <span aria-hidden="true" className="ml-0.5 text-[10px] text-muted">▾</span>
    </button>
    {open && <div role="menu" className="absolute top-[calc(100%+8px)] right-0 z-50 w-[240px] rounded-lg border border-line bg-white py-1.5 shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-2px_rgba(0,0,0,0.05)] max-tablet:w-[min(280px,calc(100vw-32px))] max-phone:-right-1 max-phone:w-[min(270px,calc(100vw-24px))]">
      <div className="px-4 pt-1.5 pb-1 text-[11px] font-semibold tracking-[0.05em] text-[#94A3B8] uppercase">{roleLabel}</div>
      <Link role="menuitem" to="/my" className={ITEM_CLASS}>Dasbor</Link>
      <Link role="menuitem" to="/my/courses" className={ITEM_CLASS}>Kursus saya</Link>
      <Link role="menuitem" to="/user/profile" className={ITEM_CLASS}>Profil</Link>
      <div className="my-1.5 h-px bg-line" />
      <button type="button" role="menuitem" className={ITEM_CLASS} onClick={onLogout}>Keluar</button>
    </div>}
  </div>;
}
