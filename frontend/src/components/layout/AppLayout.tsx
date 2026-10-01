import React from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { AuthUser } from '../../types/auth'
import { AppNavbar } from './AppNavbar'
import { Toast, type ToastItem } from '../ui/Toast'
import styles from './AppLayout.module.css'

interface AppLayoutProps {
  currentPath: AppPath
  currentUser: AuthUser | null
  onNavigate: (path: AppPath) => void
  onLogout: () => void
  onOpenModal: (modal: ModalType) => void
  toasts: ToastItem[]
  onDismissToast: (id: string) => void
  children: React.ReactNode
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPath,
  currentUser,
  onNavigate,
  onLogout,
  onOpenModal,
  toasts,
  onDismissToast,
  children,
}) => {
  return (
    <div className={styles.pageContainer}>
      <AppNavbar
        currentPath={currentPath}
        currentUser={currentUser}
        onNavigate={onNavigate}
        onLogout={onLogout}
        onOpenModal={onOpenModal}
      />
      <div className={styles.mainContent}>{children}</div>
      <Toast toasts={toasts} onDismiss={onDismissToast} />
    </div>
  )
}
