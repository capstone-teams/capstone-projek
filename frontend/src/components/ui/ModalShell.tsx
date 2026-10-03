import React, { useEffect, useRef } from 'react'
import styles from './ModalShell.module.css'

export interface ModalShellProps {
  isOpen?: boolean
  onClose: () => void
  title: string
  titleId?: string
  maxWidth?: string
  children: React.ReactNode
}

export const ModalShell: React.FC<ModalShellProps> = ({
  isOpen = true,
  onClose,
  title,
  titleId = 'modal-title',
  maxWidth,
  children,
}) => {
  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    // Body scroll lock
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }

      // Focus trap within modal
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (focusable.length > 0) {
          const first = focusable[0]
          const last = focusable[focusable.length - 1]

          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault()
            last.focus()
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault()
            first.focus()
          }
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    modalRef.current?.focus()

    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div
      className={styles.modalBackdrop}
      onClick={handleBackdropClick}
      role="presentation"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className={styles.modalCard}
        style={maxWidth ? { maxWidth } : undefined}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className={styles.modalHeader}>
          <h2 id={titleId} className={styles.modalTitle}>
            {title}
          </h2>
          <button
            type="button"
            className={styles.modalCloseBtn}
            onClick={onClose}
            aria-label="Tutup modal"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
