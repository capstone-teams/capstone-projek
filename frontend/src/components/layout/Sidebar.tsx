import type { ReactNode } from 'react'
import {
  IconLogo,
  IconGrid,
  IconBook,
  IconClipboard,
  IconLayers,
  IconCloud,
  IconUser,
  IconChevronDown,
} from '../icons/Icons'
import styles from './Sidebar.module.css'

export type NavTabId =
  | 'dashboard'
  | 'rps'
  | 'course-plan'
  | 'content'
  | 'moodle'
  | 'profile'

interface NavItem {
  id: NavTabId
  label: string
  icon: ReactNode
  badge?: string
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <IconGrid size={18} /> },
  { id: 'rps', label: 'RPS', icon: <IconBook size={18} /> },
  { id: 'course-plan', label: 'Course Plan', icon: <IconClipboard size={18} /> },
  { id: 'content', label: 'Konten Pembelajaran', icon: <IconLayers size={18} /> },
  { id: 'moodle', label: 'Moodle', icon: <IconCloud size={18} /> },
  { id: 'profile', label: 'Profil Dosen', icon: <IconUser size={18} /> },
]

export interface SidebarProps {
  activeTab: NavTabId
  onSelectTab: (id: NavTabId) => void
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({
  activeTab,
  onSelectTab,
  isOpen = false,
  onClose,
}: SidebarProps) {
  return (
    <>
      {isOpen && <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />}
      <aside
        className={`${styles.sidebar} ${isOpen ? styles.sidebarOpen : ''}`}
        aria-label="Navigasi Utama"
      >
        <div>
          <div className={styles.brandContainer}>
            <IconLogo size={34} />
            <div className={styles.brandText}>
              <span className={styles.brandTitle}>Agentic LMS</span>
              <span className={styles.brandSubtitle}>Institut Teknologi Kalimantan</span>
            </div>
          </div>

          <nav className={styles.nav}>
            {navItems.map((item) => {
              const isActive = activeTab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    onSelectTab(item.id)
                    onClose?.()
                  }}
                  className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {item.icon}
                  <span className={styles.navLabel}>{item.label}</span>
                  {item.badge && <span className={styles.navBadge}>{item.badge}</span>}
                </button>
              )
            })}
          </nav>
        </div>

        <div className={styles.footerContainer}>
          <div
            className={styles.userCard}
            role="button"
            tabIndex={0}
            onClick={() => onSelectTab('profile')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                onSelectTab('profile')
              }
            }}
          >
            <div className={styles.avatar}>MC</div>
            <div className={styles.userInfo}>
              <span className={styles.userName}>Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.</span>
              <span className={styles.userRole}>Dosen Pengampu</span>
            </div>
            <IconChevronDown size={14} className={styles.chevronIcon} />
          </div>
        </div>
      </aside>
    </>
  )
}
