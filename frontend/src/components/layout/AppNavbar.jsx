import { useState, useEffect, useRef } from 'react';
import { DOSEN_PROFILE, MAHASISWA_PROFILE } from '../../types/auth';
import { useAuth } from '../../hooks/useAuth';
import styles from './AppNavbar.module.css';
export const AppNavbar = ({ currentPath, activeRole, dosenProfile = DOSEN_PROFILE, onNavigate, onOpenModal, }) => {
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const menuRef = useRef(null);
    const isLoginPage = currentPath === '/login';
    const isDosen = activeRole === 'dosen';
    const { user } = useAuth();
    const currentProfile = isDosen ? dosenProfile : {
        ...MAHASISWA_PROFILE,
        name: user?.name ?? MAHASISWA_PROFILE.name,
        avatarInitial: user?.name?.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() ?? MAHASISWA_PROFILE.avatarInitial,
    };
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setDropdownOpen(false);
            }
        };
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                setDropdownOpen(false);
            }
        };
        if (dropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            document.addEventListener('keydown', handleKeyDown);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [dropdownOpen]);
    const handleBrandClick = () => {
        if (isLoginPage) {
            onNavigate('/login');
            return;
        }
        if (isDosen) {
            onNavigate('/dashboard');
        }
        else {
            onNavigate('/student/courses');
        }
    };
    return (<header className={styles.header}>
      <div className={styles.headerInner}>
        <div className={styles.brand} onClick={handleBrandClick} role="button" tabIndex={0} onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleBrandClick();
            }
        }}>
          <div className={styles.brandLogo} aria-hidden="true">
            ITK
          </div>
          <span className={styles.brandTitle}>Agentic LMS</span>
          <span className={styles.brandSubtitle}>· Institut Teknologi Kalimantan</span>
        </div>

        {!isLoginPage ? (<div className={styles.userMenuContainer} ref={menuRef}>
            <button type="button" className={styles.userPill} onClick={() => setDropdownOpen((prev) => !prev)} aria-expanded={dropdownOpen} aria-haspopup="menu">
              <span className={styles.avatarBadge}>{currentProfile.avatarInitial}</span>
              <span className={styles.userName}>{currentProfile.name}</span>
              <span className={styles.dropdownArrow}>▾</span>
            </button>

            {dropdownOpen && (<div className={styles.dropdownMenu} role="menu">
                {isDosen && (<button type="button" className={styles.dropdownItem} role="menuitem" onClick={() => {
                        setDropdownOpen(false);
                        onOpenModal('profile');
                    }}>
                    <span>Profil Dosen</span>
                  </button>)}

                <div className={styles.dropdownDivider}/>

                <div className={styles.dropdownSection}>Akun aktif</div>
                <div className={styles.dropdownItem}>{isDosen ? 'Dosen' : 'Mahasiswa'} ({currentProfile.name})</div>
                <div className={styles.dropdownDivider}/>

                <button type="button" className={styles.dropdownItem} role="menuitem" onClick={() => {
                    setDropdownOpen(false);
                    onNavigate('/login');
                }}>
                  <span style={{ color: '#DC2626', fontWeight: 500 }}>Keluar (Logout)</span>
                </button>
              </div>)}
          </div>) : (<button type="button" className={styles.userPill} onClick={() => onNavigate('/login')}>
            <span>Masuk</span>
          </button>)}
      </div>
    </header>);
};
