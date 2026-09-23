import React from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { CoursePlanStage, SyllabusWeek } from '../../types/course'
import { WEEKS_DATA } from '../../data/courseData'
import styles from './CoursePlanPage.module.css'

interface CoursePlanPageProps {
  stage: CoursePlanStage
  onStageChange: (newStage: CoursePlanStage) => void
  onNavigate: (path: AppPath) => void
  onOpenModal: (modal: ModalType) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const CoursePlanPage: React.FC<CoursePlanPageProps> = ({
  stage,
  onStageChange,
  onNavigate,
  onOpenModal,
  onShowToast,
}) => {
  const group1 = WEEKS_DATA.slice(0, 4)
  const group2 = WEEKS_DATA.slice(4, 8)
  const group3 = WEEKS_DATA.slice(8, 12)
  const group4 = WEEKS_DATA.slice(12, 16)

  const isMoodle = (weekNum: number) => stage === 'published' && weekNum <= 3

  const renderGroup = (title: string, weeks: SyllabusWeek[]) => (
    <div className={styles.weekGroup}>
      <h3 className={styles.weekGroupTitle}>{title}</h3>
      <div className={styles.weekGrid}>
        {weeks.map((w) => {
          const published = isMoodle(w.weekNumber)
          const isWeek3 = w.weekNumber === 3
          const handleWeekClick = () => {
            onNavigate('/weekly-content')
          }

          let badgeClass = styles.badgeDraft
          let badgeText = 'Draft'

          if (stage === 'approved') {
            badgeClass = styles.badgeSuccess
            badgeText = 'Disetujui'
          } else if (stage === 'published') {
            if (published) {
              badgeClass = styles.badgeMoodle
              badgeText = 'Tersedia di Moodle'
            } else {
              badgeClass = styles.badgeSuccess
              badgeText = 'Disetujui'
            }
          }

          return (
            <div
              key={w.weekNumber}
              className={styles.weekCard}
              onClick={handleWeekClick}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  handleWeekClick()
                }
              }}
              style={isWeek3 ? { border: '2px solid #3B82F6' } : undefined}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className={styles.weekCardNumber}>
                    Minggu {w.weekNumber < 10 ? `0${w.weekNumber}` : w.weekNumber}
                  </span>
                </div>
                <h4 className={styles.weekCardTitle}>{w.title}</h4>
              </div>

              <div className={styles.weekCardFooter}>
                <span className={badgeClass}>{badgeText}</span>
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
          onClick={() => onNavigate('/dashboard')}
        >
          Dashboard
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Keamanan Siber</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Keamanan Siber</h1>
          <p className={styles.pageSubtitle}>
            {stage === 'empty'
              ? 'Course Plan · 16 pertemuan · IF403 · 3 SKS · Belum Ada Rencana'
              : stage === 'review'
              ? 'Course Plan · 16 pertemuan · IF403 · 3 SKS · Versi 1 (Siap Ditinjau)'
              : stage === 'approved'
              ? 'Course Plan · 16 pertemuan · IF403 · 3 SKS · Disetujui Dosen · Siap Penyusunan Konten'
              : 'Course Plan · 16 pertemuan · IF403 · 3 SKS · 3 Minggu Terbit di Moodle ITK'}
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() => onNavigate('/rps-analysis')}
          >
            Lihat Analisis RPS
          </button>
        </div>
      </div>

      {/* Conditional Lifecycle Rendering */}
      {stage === 'empty' && (
        <div className={styles.emptyCard}>
          <h2 className={styles.emptyTitle}>Course Plan belum tersedia</h2>
          <p className={styles.emptyDesc}>
            Gunakan hasil analisis RPS untuk menyusun rencana pembelajaran 16 pertemuan secara otomatis oleh Agent AI.
          </p>
          <button
            type="button"
            className={styles.btnPrimary}
            style={{ width: '220px', height: '44px' }}
            onClick={() => onOpenModal('generate-plan')}
          >
            Generate Course Plan
          </button>
        </div>
      )}

      {stage === 'review' && (
        <>
          <div className={styles.statusBanner}>
            <div className={styles.statusText}>
              <h2 className={styles.statusHeading}>Rencana siap ditinjau</h2>
              <p className={styles.statusDesc}>
                Periksa topik dan tujuan tiap minggu sebelum membuat konten. Anda dapat meminta revisi atau menyetujui.
              </p>
            </div>

            <div className={styles.statusActions}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() => onOpenModal('plan-revision')}
              >
                Minta Revisi
              </button>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() => {
                  onStageChange('approved')
                  onShowToast?.('Course Plan disetujui. Anda dapat mulai menyusun konten mingguan.', 'success')
                }}
              >
                Setujui Course Plan
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {renderGroup('Pertemuan 1–4', group1)}
            {renderGroup('Pertemuan 5–8', group2)}
            {renderGroup('Pertemuan 9–12', group3)}
            {renderGroup('Pertemuan 13–16', group4)}
          </div>
        </>
      )}

      {stage === 'approved' && (
        <>
          <div className={styles.statusBanner}>
            <div className={styles.statusText}>
              <h2 className={styles.statusHeading}>
                Rencana disetujui · Siap membuat konten mingguan
              </h2>
              <p className={styles.statusDesc}>
                Klik modul pertemuan (misal: Minggu 03) untuk mulai menyiapkan materi, resource, dan tugas.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {renderGroup('Pertemuan 1–4', group1)}
            {renderGroup('Pertemuan 5–8', group2)}
            {renderGroup('Pertemuan 9–12', group3)}
            {renderGroup('Pertemuan 13–16', group4)}
          </div>
        </>
      )}

      {stage === 'published' && (
        <>
          <div className={styles.statusBanner}>
            <div className={styles.statusText}>
              <h2 className={styles.statusHeading}>
                Rencana disetujui · 3 minggu tersedia di Moodle
              </h2>
              <p className={styles.statusDesc}>
                Minggu 1–3 telah dipublikasikan ke LMS Moodle ITK. Minggu 4–16 siap diproses selanjutnya.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {renderGroup('Pertemuan 1–4', group1)}
            {renderGroup('Pertemuan 5–8', group2)}
            {renderGroup('Pertemuan 9–12', group3)}
            {renderGroup('Pertemuan 13–16', group4)}
          </div>
        </>
      )}
    </div>
  )
}
