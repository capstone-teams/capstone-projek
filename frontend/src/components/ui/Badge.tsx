import type { ReactNode } from 'react'
import styles from './Badge.module.css'

export type BadgeVariant = 'success' | 'info' | 'warning' | 'purple' | 'neutral'

export interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
  withDot?: boolean
  className?: string
}

export function Badge({
  children,
  variant = 'neutral',
  withDot = true,
  className = '',
}: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[variant]} ${className}`.trim()}>
      {withDot && <span className={styles.dot} aria-hidden="true" />}
      <span>{children}</span>
    </span>
  )
}
