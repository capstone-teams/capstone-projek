import React from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { UserRole, UserProfile } from '../../types/auth'
import { AppNavbar } from './AppNavbar'
import { Toast, type ToastItem } from '../ui/Toast'
import styles from './AppLayout.module.css'

interface AppLayoutProps {
  currentPath: AppPath
  activeRole: UserRole
  dosenProfile?: UserProfile
  onNavigate: (path: AppPath) => void
  onRoleChange: (role: UserRole) => void
  onOpenModal: (modal: ModalType) => void
  toasts: ToastItem[]
  onDismissToast: (id: string) => void
  children: React.ReactNode
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPath,
  activeRole,
  dosenProfile,
  onNavigate,
  onRoleChange,
  onOpenModal,
  toasts,
  onDismissToast,
  children,
}) => {
  return (
    <div className={styles.pageContainer}>
      <AppNavbar
        currentPath={currentPath}
        activeRole={activeRole}
        dosenProfile={dosenProfile}
        onNavigate={onNavigate}
        onRoleChange={onRoleChange}
        onOpenModal={onOpenModal}
      />
      <div className={styles.mainContent}>{children}</div>
      <Toast toasts={toasts} onDismiss={onDismissToast} />
    </div>
  )
}
