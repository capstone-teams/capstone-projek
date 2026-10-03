import type { HTMLAttributes, ReactNode } from 'react'
import styles from './Card.module.css'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  padding?: 'none' | 'sm' | 'md' | 'lg'
  interactive?: boolean
  className?: string
}

export function Card({
  children,
  padding = 'md',
  interactive = false,
  className = '',
  ...props
}: CardProps) {
  const paddingClass =
    padding === 'none'
      ? styles.paddingNone
      : padding === 'sm'
      ? styles.paddingSm
      : padding === 'lg'
      ? styles.paddingLg
      : styles.paddingMd

  return (
    <div
      className={`${styles.card} ${paddingClass} ${
        interactive ? styles.interactive : ''
      } ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  )
}
