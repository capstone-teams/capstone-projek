import React from 'react'
import type { AppPath } from '../../types/navigation'
import { MAHASISWA_COURSES } from '../../data/courseData'
import { MAHASISWA_PROFILE } from '../../types/auth'
import styles from './Student.module.css'

interface StudentCoursesPageProps {
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const StudentCoursesPage: React.FC<StudentCoursesPageProps> = ({
  onNavigate,
  onShowToast,
}) => {
  const handleCourseClick = (code: string, name: string) => {
    if (code === 'IF201405' || code === 'IF403') {
      onNavigate('/student/course')
    } else {
      onShowToast?.(
        `Silabus ${name} (${code}) sedang dalam penyusunan dosen. Buka Aljabar Linear dan Geometri untuk materi aktif.`,
        'info'
      )
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Mata Kuliah Saya</h1>
          <p className={styles.pageSubtitle}>
            {MAHASISWA_PROFILE.name} · Semester Gasal 2026/2027
          </p>
        </div>
      </div>

      <div className={styles.courseGrid}>
        {MAHASISWA_COURSES.map((c) => (
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
              <span className={styles.courseMeta}>{c.dosen}</span>
              <span className={styles.courseMeta} style={{ fontSize: '12px' }}>
                {c.sks}
              </span>
            </div>

            <div className={styles.courseCardFooter}>
              <span
                className={
                  c.badgeType === 'moodle' ? styles.badgeMoodle : styles.badgeSuccess
                }
              >
                {c.badge}
              </span>
              <span style={{ fontSize: '12px', color: '#64748B' }}>{c.available}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
