import React from 'react'
import type { AppPath } from '../../types/navigation'
import type { SyllabusWeek } from '../../types/course'
import { WEEKS_DATA } from '../../data/courseData'
import styles from './Student.module.css'

interface StudentCourseDetailPageProps {
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const StudentCourseDetailPage: React.FC<StudentCourseDetailPageProps> = ({
  onNavigate,
  onShowToast,
}) => {
  const group1 = WEEKS_DATA.slice(0, 4)
  const group2 = WEEKS_DATA.slice(4, 8)
  const group3 = WEEKS_DATA.slice(8, 12)
  const group4 = WEEKS_DATA.slice(12, 16)

  const isAvailable = (weekNum: number) => weekNum <= 3

  const renderGroup = (title: string, weeks: SyllabusWeek[]) => (
    <div className={styles.weekGroup}>
      <h3 className={styles.weekGroupTitle}>{title}</h3>
      <div className={styles.weekGrid}>
        {weeks.map((w) => {
          const avail = isAvailable(w.weekNumber)
          const handleWeekClick = () => {
            if (avail) {
              onNavigate('/student/week')
            }
          }

          return (
            <div
              key={w.weekNumber}
              className={`${styles.weekCard} ${avail ? styles.weekCardHover : ''}`}
              onClick={handleWeekClick}
              role={avail ? 'button' : undefined}
              tabIndex={avail ? 0 : undefined}
              onKeyDown={(e) => {
                if (avail && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault()
                  handleWeekClick()
                }
              }}
              style={{
                opacity: avail ? 1 : 0.75,
                cursor: avail ? 'pointer' : 'default',
              }}
            >
              <div>
                <span className={styles.weekCardNumber}>
                  Minggu {w.weekNumber < 10 ? `0${w.weekNumber}` : w.weekNumber}
                </span>
                <h4 className={styles.weekCardTitle}>{w.title}</h4>
              </div>

              <div className={styles.weekCardFooter}>
                {avail ? (
                  <span className={styles.badgeMoodle}>Tersedia di Moodle</span>
                ) : (
                  <span className={styles.badgePending}>Belum tersedia</span>
                )}
                <span style={{ fontSize: '11px', color: '#64748B' }}>
                  3 SKS · Minggu {w.weekNumber < 10 ? `0${w.weekNumber}` : w.weekNumber}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  return (
    <div className={styles.container}>
      {/* Breadcrumb links */}
      <div className={styles.breadcrumbs}>
        <button
          type="button"
          className={styles.breadcrumbLink}
          onClick={() => onNavigate('/student/courses')}
        >
          Mata Kuliah
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Keamanan Siber</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Keamanan Siber</h1>
          <p className={styles.pageSubtitle}>
            Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom. · IF403 · 3 SKS
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() =>
              onShowToast?.('Membuka Course Keamanan Siber di Moodle ITK...', 'info')
            }
          >
            Buka Course di Moodle
          </button>
        </div>
      </div>

      {/* Ringkasan course */}
      <div className={styles.statusBanner}>
        <div className={styles.statusText}>
          <h2 className={styles.statusHeading}>Overview mata kuliah</h2>
          <p className={styles.statusDesc}>
            Konsep, ancaman, dan praktik keamanan sistem informasi.
          </p>
        </div>

        <div className={styles.statusActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() =>
              onShowToast?.('Membuka dokumen RPS Keamanan Siber...', 'info')
            }
          >
            Lihat RPS
          </button>
        </div>
      </div>

      {/* 16 Pertemuan Mingguan */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {renderGroup('Pertemuan 1–4', group1)}
        {renderGroup('Pertemuan 5–8', group2)}
        {renderGroup('Pertemuan 9–12', group3)}
        {renderGroup('Pertemuan 13–16', group4)}
      </div>
    </div>
  )
}
