import React, { useState, useEffect, useRef } from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { UserRole, UserProfile } from '../../types/auth'
import { DOSEN_PROFILE, MAHASISWA_PROFILE } from '../../types/auth'
import styles from './AppNavbar.module.css'

interface AppNavbarProps {
  currentPath: AppPath
  activeRole: UserRole
  dosenProfile?: UserProfile
  onNavigate: (path: AppPath) => void
  onRoleChange: (role: UserRole) => void
  onOpenModal: (modal: ModalType) => void
}

export const AppNavbar: React.FC<AppNavbarProps> = ({
  currentPath,
  activeRole,
  dosenProfile = DOSEN_PROFILE,
  onNavigate,
  onRoleChange,
  onOpenModal,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const isLoginPage = currentPath === '/login'
  const isDosen = activeRole === 'dosen'
  const currentProfile = isDosen ? dosenProfile : MAHASISWA_PROFILE

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
    if (isLoginPage) {
      onNavigate('/login')
      return
    }
    if (isDosen) {
      onNavigate('/dashboard')
    } else {
      onNavigate('/student/courses')
    }
  }

  const handleSwitchToDosen = () => {
    setDropdownOpen(false)
    onRoleChange('dosen')
    onNavigate('/dashboard')
  }

  const handleSwitchToMahasiswa = () => {
    setDropdownOpen(false)
    onRoleChange('mahasiswa')
    onNavigate('/student/courses')
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

        {!isLoginPage ? (
          <div className={styles.userMenuContainer} ref={menuRef}>
            <button
              type="button"
              className={styles.userPill}
              onClick={() => setDropdownOpen((prev) => !prev)}
              aria-expanded={dropdownOpen}
              aria-haspopup="menu"
            >
              <span className={styles.avatarBadge}>{currentProfile.avatarInitial}</span>
              <span className={styles.userName}>{currentProfile.name}</span>
              <span className={styles.dropdownArrow}>▾</span>
            </button>

            {dropdownOpen && (
              <div className={styles.dropdownMenu} role="menu">
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

                <div className={styles.dropdownDivider} />

                <div className={styles.dropdownSection}>Ganti Perspektif</div>

                <button
                  type="button"
                  className={styles.dropdownItem}
                  role="menuitem"
                  onClick={handleSwitchToDosen}
                >
                  <span>Dosen ({dosenProfile.name})</span>
                  {isDosen && <span style={{ color: '#2563EB', fontWeight: 700 }}>✓</span>}
                </button>

                <button
                  type="button"
                  className={styles.dropdownItem}
                  role="menuitem"
                  onClick={handleSwitchToMahasiswa}
                >
                  <span>Mahasiswa ({MAHASISWA_PROFILE.name})</span>
                  {!isDosen && <span style={{ color: '#2563EB', fontWeight: 700 }}>✓</span>}
                </button>

                <div className={styles.dropdownDivider} />

                <button
                  type="button"
                  className={styles.dropdownItem}
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false)
                    onNavigate('/login')
                  }}
                >
                  <span style={{ color: '#DC2626', fontWeight: 500 }}>Keluar (Logout)</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            className={styles.userPill}
            onClick={() => onNavigate('/login')}
          >
            <span>Masuk</span>
          </button>
        )}
      </div>
    </header>
  )
}
