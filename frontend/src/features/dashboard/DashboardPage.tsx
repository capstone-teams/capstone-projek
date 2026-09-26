import React from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import { DOSEN_COURSES } from '../../data/courseData'
import styles from './DashboardPage.module.css'

interface DashboardPageProps {
  onNavigate: (path: AppPath) => void
  onOpenModal: (modal: ModalType) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
  hasCourses?: boolean
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  onOpenModal,
  onShowToast,
  hasCourses = false,
}) => {
  const handleCourseClick = (code: string, name: string) => {
    if (code === 'IF201405' || code === 'IF403') {
      onNavigate('/course-plan')
    } else {
      onShowToast?.(
        `Course Plan ${name} (${code}) sedang dalam penyusunan. Buka Aljabar Linear dan Geometri untuk melihat Course Plan aktif.`,
        'info'
      )
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Mata Kuliah Dosen</h1>
          <p className={styles.pageSubtitle}>
            Semester Gasal 2026/2027 · Institut Teknologi Kalimantan
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={() => onOpenModal('upload-rps')}
          >
            + Upload RPS
          </button>
        </div>
      </div>

      {!hasCourses ? (
        <div className={styles.emptyCard}>
          <h2 className={styles.emptyTitle}>Belum ada mata kuliah</h2>
          <p className={styles.emptyDesc}>
            Unggah RPS pertama untuk menyiapkan rencana dan konten pembelajaran.
          </p>
          <div className={styles.emptyActions}>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={() => onOpenModal('upload-rps')}
            >
              Upload RPS
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.courseGrid}>
          {DOSEN_COURSES.map((c) => (
            <div
              key={c.code}
              className={styles.courseCard}
              onClick={() => handleCourseClick(c.code, c.name)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  handleCourseClick(c.code, c.name)
                }
              }}
            >
              <div className={styles.courseCardHeader}>
                <span className={styles.courseCode}>{c.code}</span>
                <h3 className={styles.courseName}>{c.name}</h3>
                <span className={styles.courseMeta}>{c.sks}</span>
                <span className={styles.courseMeta} style={{ fontSize: '12px' }}>
                  {c.semester}
                </span>
              </div>

              <div className={styles.courseCardFooter}>
                <span
                  className={
                    c.badgeType === 'moodle'
                      ? styles.badgeMoodle
                      : c.badgeType === 'approved'
                      ? styles.badgeSuccess
                      : styles.badgeDraft
                  }
                >
                  {c.badge}
                </span>
                <span style={{ fontSize: '12px', color: '#64748B' }}>{c.progress}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
