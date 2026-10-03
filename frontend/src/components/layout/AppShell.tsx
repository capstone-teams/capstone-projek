import { useState, type ReactNode } from 'react'
import { Sidebar, type NavTabId } from './Sidebar'
import { Header } from './Header'
import styles from './AppShell.module.css'

export interface AppShellProps {
  children: ReactNode
  activeTab: NavTabId
  onSelectTab: (tab: NavTabId) => void
  title: string
  breadcrumb?: string
}

export function AppShell({
  children,
  activeTab,
  onSelectTab,
  title,
  breadcrumb,
}: AppShellProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <div className={styles.shell}>
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />
      <div className={styles.contentWrapper}>
        <Header
          title={title}
          breadcrumb={breadcrumb}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
        />
        <main className={styles.mainContainer}>{children}</main>
      </div>
    </div>
  )
}
