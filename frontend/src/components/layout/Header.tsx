import { IconBell, IconChevronDown } from '../icons/Icons'
import styles from './Header.module.css'

export interface HeaderProps {
  title: string
  breadcrumb?: string
  onToggleMobileMenu?: () => void
}

export function Header({
  title,
  breadcrumb = 'Agentic LMS / ITK',
  onToggleMobileMenu,
}: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.leftSection}>
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className={styles.mobileMenuButton}
          aria-label="Buka Menu Navigasi"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <div className={styles.titleArea}>
          <span className={styles.breadcrumb}>{breadcrumb}</span>
          <h1 className={styles.pageTitle}>{title}</h1>
        </div>
      </div>

      <div className={styles.rightSection}>
        <button
          type="button"
          className={styles.notificationButton}
          aria-label="Pemberitahuan"
        >
          <IconBell size={18} />
          <span className={styles.notificationIndicator} />
        </button>

        <div
          className={styles.userPill}
          role="button"
          tabIndex={0}
          aria-label="Profil Pengguna"
        >
          <div className={styles.pillAvatar}>MC</div>
          <span className={styles.pillName}>Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.</span>
          <IconChevronDown size={14} className={styles.chevronIcon} />
        </div>
      </div>
    </header>
  )
}
