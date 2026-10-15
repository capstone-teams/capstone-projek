import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import UserMenu from './UserMenu';

const NAV_LINK_CLASS =
  'box-border inline-flex h-full items-center border-b-2 border-transparent px-3.5 text-[14px] font-medium whitespace-nowrap text-muted no-underline transition-colors duration-150 ease-[ease] hover:text-ink aria-[current=page]:border-b-primary aria-[current=page]:font-semibold aria-[current=page]:text-primary max-tablet:px-2.5 max-tablet:text-[13px] max-phone:px-2 max-phone:text-[12px]';

/** Header atas aplikasi: logo, navigasi utama (setelah login), dan menu user. */
export default function ApplicationHeader() {
  const { user, logout } = useAuth();
  return <header className="sticky top-0 z-40 box-border h-16 border-b border-line bg-white">
    <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between gap-4 px-16 max-laptop:px-8 max-tablet:px-4 max-phone:gap-2 max-phone:px-3">
      <div className="flex h-full min-w-0 items-center gap-8 max-laptop:gap-5 max-tablet:gap-4 max-phone:gap-2 max-phone:overflow-x-auto max-phone:[scrollbar-width:none] max-phone:[&::-webkit-scrollbar]:hidden">
        <Link to={user ? '/my' : '/login'} className="flex min-w-0 cursor-pointer items-center gap-2.5 text-[18px] font-bold text-ink no-underline select-none hover:text-ink hover:opacity-90 max-phone:shrink-0 max-phone:gap-2">
          <img src="/itk-logo.png" alt="ITK" className="block h-9 w-auto max-w-[90px] shrink-0 object-contain max-tablet:h-[30px] max-phone:h-[26px]" />
          <span className="truncate text-[18px] font-bold tracking-[-0.01em] text-ink max-tablet:text-[16px] max-phone:hidden">Agentic LMS</span>
        </Link>
        {user && <nav className="flex h-full items-center gap-1 max-phone:gap-0.5" aria-label="Navigasi situs">
          <NavLink to="/my" end className={NAV_LINK_CLASS}>Dasbor</NavLink>
          <NavLink to="/my/courses" className={NAV_LINK_CLASS}>Kursusku</NavLink>
        </nav>}
      </div>
      {user && <div className="flex shrink-0 items-center gap-4 max-phone:gap-2">
        <UserMenu user={user} onLogout={logout} />
      </div>}
    </div>
  </header>;
}
