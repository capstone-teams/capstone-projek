import React, { useState, useEffect, useRef } from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { AuthUser } from '../../types/auth'
import { getDefaultPathForRole, getNavigationForRole } from '../../utils/navigation'
import styles from './AppNavbar.module.css'

interface AppNavbarProps {
  currentPath: AppPath
  currentUser: AuthUser | null
  onNavigate: (path: AppPath) => void
  onLogout: () => void
  onOpenModal: (modal: ModalType) => void
}

export const AppNavbar: React.FC<AppNavbarProps> = ({
  currentPath,
  currentUser,
  onNavigate,
  onLogout,
  onOpenModal,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const isLoginPage = currentPath === '/login'
  const isDosen = currentUser?.role === 'INSTRUCTOR'
  const navItems = currentUser ? getNavigationForRole(currentUser.role) : []

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDropdownOpen(false)
      }
    }

    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [dropdownOpen])

  const handleBrandClick = () => {
    onNavigate(currentUser ? getDefaultPathForRole(currentUser.role) : '/login')
  }

  const handleNavItemClick = (path: AppPath) => {
    setDropdownOpen(false)
    onNavigate(path)
  }

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <div
          className={styles.brand}
          onClick={handleBrandClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              handleBrandClick()
            }
          }}
        >
          <div className={styles.brandLogo} aria-hidden="true">
            ITK
          </div>
          <span className={styles.brandTitle}>Agentic LMS</span>
          <span className={styles.brandSubtitle}>· Institut Teknologi Kalimantan</span>
        </div>

        {navItems.length > 0 && (
          <nav className={styles.primaryNav} aria-label="Navigasi utama">
            {navItems.map((item) => (
              <button
                key={item.path}
                type="button"
                className={`${styles.navLink} ${item.path === currentPath ? styles.navLinkActive : ''}`.trim()}
                aria-current={item.path === currentPath ? 'page' : undefined}
                onClick={() => onNavigate(item.path)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        )}

        {currentUser ? (
          <div className={styles.userMenuContainer} ref={menuRef}>
            <button
              type="button"
              className={styles.userPill}
              onClick={() => setDropdownOpen((prev) => !prev)}
              aria-expanded={dropdownOpen}
              aria-haspopup="menu"
            >
              <span className={styles.avatarBadge}>{currentUser.profile.avatarInitial}</span>
              <span className={styles.userName}>{currentUser.profile.name}</span>
              <span className={styles.dropdownArrow}>▾</span>
            </button>

            {dropdownOpen && (
              <div className={styles.dropdownMenu} role="menu">
                <div className={styles.mobileNavSection}>
                  <div className={styles.dropdownSection}>Navigasi</div>
                  {navItems.map((item) => (
                    <button
                      key={item.path}
                      type="button"
                      className={styles.dropdownItem}
                      role="menuitem"
                      onClick={() => handleNavItemClick(item.path)}
                    >
                      <span>{item.label}</span>
                    </button>
                  ))}
                  <div className={styles.dropdownDivider} />
                </div>

                {isDosen && (
                  <button
                    type="button"
                    className={styles.dropdownItem}
                    role="menuitem"
                    onClick={() => {
                      setDropdownOpen(false)
                      onOpenModal('profile')
                    }}
                  >
                    <span>Profil Dosen</span>
                  </button>
                )}

                {isDosen && <div className={styles.dropdownDivider} />}

                <button
                  type="button"
                  className={styles.dropdownItem}
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false)
                    onLogout()
                  }}
                >
                  <span style={{ color: '#DC2626', fontWeight: 500 }}>Keluar (Logout)</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          !isLoginPage && (
            <button
              type="button"
              className={styles.userPill}
              onClick={() => onNavigate('/login')}
            >
              <span>Masuk</span>
            </button>
          )
        )}
      </div>
    </header>
  )
}
