import React, { useState, useEffect } from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { CoursePlanStage, SyllabusWeek } from '../../types/course'
import { WEEKS_DATA } from '../../data/courseData'
import styles from './CoursePlanPage.module.css'

interface CoursePlanPageProps {
  stage: CoursePlanStage
  onStageChange: (newStage: CoursePlanStage) => void
  allWeeksGenerated?: boolean
  onAutoGenerateAllWeeks?: () => void
  onSelectWeek?: (weekNumber: number) => void
  onNavigate: (path: AppPath) => void
  onOpenModal: (modal: ModalType) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const CoursePlanPage: React.FC<CoursePlanPageProps> = ({
  stage,
  onStageChange,
  allWeeksGenerated = false,
  onAutoGenerateAllWeeks,
  onSelectWeek,
  onNavigate,
  onOpenModal,
  onShowToast,
}) => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStep, setGenerationStep] = useState(1)
  const [progressPercent, setProgressPercent] = useState(25)

  const [isBatchGenerating, setIsBatchGenerating] = useState(false)
  const [batchWeek, setBatchWeek] = useState(1)
  const [batchStep, setBatchStep] = useState(1)
  const [batchProgressPercent, setBatchProgressPercent] = useState(10)

  useEffect(() => {
    if (!isGenerating) return

    const t1 = setTimeout(() => {
      setGenerationStep(2)
      setProgressPercent(55)
    }, 600)

    const t2 = setTimeout(() => {
      setGenerationStep(3)
      setProgressPercent(80)
    }, 1300)

    const t3 = setTimeout(() => {
      setGenerationStep(4)
      setProgressPercent(100)
    }, 2000)

    const t4 = setTimeout(() => {
      setIsGenerating(false)
      onStageChange('review')
      onShowToast?.(
        'Course Plan 16 pertemuan berhasil disusun oleh Agent AI berdasarkan profil dosen & RPS.',
        'success'
      )
    }, 2500)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
    }
  }, [isGenerating, onStageChange, onShowToast])

  useEffect(() => {
    if (!isBatchGenerating) return

    const t1 = setTimeout(() => {
      setBatchWeek(4)
      setBatchStep(2)
      setBatchProgressPercent(30)
    }, 400)

    const t2 = setTimeout(() => {
      setBatchWeek(8)
      setBatchProgressPercent(55)
    }, 850)

    const t3 = setTimeout(() => {
      setBatchWeek(12)
      setBatchProgressPercent(75)
    }, 1350)

    const t4 = setTimeout(() => {
      setBatchWeek(16)
      setBatchStep(3)
      setBatchProgressPercent(95)
    }, 1850)

    const t5 = setTimeout(() => {
      setIsBatchGenerating(false)
      setBatchProgressPercent(100)
      onAutoGenerateAllWeeks?.()
      onShowToast?.(
        'Seluruh modul 16 pertemuan berhasil disusun oleh Agent AI berdasarkan profil dosen & RPS.',
        'success'
      )
    }, 2400)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
      clearTimeout(t5)
    }
  }, [isBatchGenerating, onAutoGenerateAllWeeks, onShowToast])

  const handleStartGenerate = () => {
    setGenerationStep(1)
    setProgressPercent(25)
    setIsGenerating(true)
  }

  const handleStartBatchGenerate = () => {
    setBatchWeek(1)
    setBatchStep(1)
    setBatchProgressPercent(10)
    setIsBatchGenerating(true)
  }

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
            onSelectWeek?.(w.weekNumber)
            onNavigate('/weekly-content')
          }

          let badgeClass = styles.badgeDraft
          let badgeText = 'Draft'

          if (stage === 'approved') {
            if (allWeeksGenerated) {
              badgeClass = styles.badgeReady
              badgeText = 'Konten Siap'
            } else {
              badgeClass = styles.badgeSuccess
              badgeText = 'Disetujui'
            }
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
        <span className={styles.breadcrumbCurrent}>Aljabar Linear dan Geometri</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Aljabar Linear dan Geometri</h1>
          <p className={styles.pageSubtitle}>
            {stage === 'empty'
              ? 'Course Plan · 16 pertemuan · IF201405 · 3 SKS · Belum Ada Rencana'
              : stage === 'review'
              ? 'Course Plan · 16 pertemuan · IF201405 · 3 SKS · Versi 1 (Siap Ditinjau)'
              : stage === 'approved'
              ? 'Course Plan · 16 pertemuan · IF201405 · 3 SKS · Disetujui Dosen · Siap Penyusunan Konten'
              : 'Course Plan · 16 pertemuan · IF201405 · 3 SKS · 3 Minggu Terbit di Moodle ITK'}
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

          {!isGenerating ? (
            <button
              type="button"
              className={styles.btnPrimary}
              style={{ width: '220px', height: '44px' }}
              onClick={handleStartGenerate}
            >
              Generate Course Plan
            </button>
          ) : (
            <div className={styles.agentMonitoringCard}>
              <div className={styles.monitoringHeader}>
                <span className={styles.pulseDot} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <h4 className={styles.monitoringTitle}>
                    Agent AI sedang menyusun Course Plan...
                  </h4>
                  <span className={styles.monitoringSubtitle}>
                    Menerapkan preferensi mengajar dari Profil Dosen & dokumen RPS
                  </span>
                </div>
              </div>

              <div className={styles.progressBarContainer}>
                <div
                  className={styles.progressBarFill}
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className={styles.stepList}>
                <div
                  className={
                    generationStep > 1
                      ? styles.stepDone
                      : generationStep === 1
                      ? styles.stepActive
                      : styles.stepPending
                  }
                >
                  {generationStep > 1 ? '✓' : generationStep === 1 ? '●' : '○'} Membaca RPS & preferensi pedagogis profil dosen
                </div>
                <div
                  className={
                    generationStep > 2
                      ? styles.stepDone
                      : generationStep === 2
                      ? styles.stepActive
                      : styles.stepPending
                  }
                >
                  {generationStep > 2 ? '✓' : generationStep === 2 ? '●' : '○'} Memetakan capaian pembelajaran (CPL & Sub-CPMK)
                </div>
                <div
                  className={
                    generationStep > 3
                      ? styles.stepDone
                      : generationStep === 3
                      ? styles.stepActive
                      : styles.stepPending
                  }
                >
                  {generationStep > 3 ? '✓' : generationStep === 3 ? '●' : '○'} Menyusun struktur 16 pertemuan Aljabar Linear dan Geometri
                </div>
                <div
                  className={
                    generationStep >= 4 ? styles.stepDone : styles.stepPending
                  }
                >
                  {generationStep >= 4
                    ? '✓ Kesesuaian materi dan beban SKS tervalidasi'
                    : '○ Memvalidasi kesesuaian materi dan beban SKS'}
                </div>
              </div>
            </div>
          )}
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
          {isBatchGenerating ? (
            <div className={styles.agentMonitoringCard} style={{ maxWidth: '100%' }}>
              <div className={styles.monitoringHeader}>
                <span className={styles.pulseDot} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <h4 className={styles.monitoringTitle}>
                    Agent AI sedang menyusun seluruh modul konten (Minggu {batchWeek} dari 16)...
                  </h4>
                  <span className={styles.monitoringSubtitle}>
                    Menerapkan silabus RPS dan preferensi mengajar dari Profil Dosen
                  </span>
                </div>
              </div>

              <div className={styles.progressBarContainer}>
                <div
                  className={styles.progressBarFill}
                  style={{ width: `${batchProgressPercent}%` }}
                />
              </div>

              <div className={styles.stepList}>
                <div
                  className={
                    batchStep > 1
                      ? styles.stepDone
                      : batchStep === 1
                      ? styles.stepActive
                      : styles.stepPending
                  }
                >
                  {batchStep > 1 ? '✓' : '●'} Membaca seluruh topik silabus & preferensi pedagogis profil dosen
                </div>
                <div
                  className={
                    batchStep > 2
                      ? styles.stepDone
                      : batchStep === 2
                      ? styles.stepActive
                      : styles.stepPending
                  }
                >
                  {batchStep > 2 ? '✓' : batchStep === 2 ? '●' : '○'} Menyusun draf materi, resource, dan latihan tugas pertemuan 1–16
                </div>
                <div
                  className={
                    batchStep >= 3 ? styles.stepDone : styles.stepPending
                  }
                >
                  {batchStep >= 3
                    ? '✓ Seluruh modul 16 pertemuan tervalidasi dan siap ditinjau'
                    : '○ Memvalidasi kelengkapan modul materi'}
                </div>
              </div>
            </div>
          ) : allWeeksGenerated ? (
            <div className={styles.statusBanner}>
              <div className={styles.statusText}>
                <h2 className={styles.statusHeading}>
                  Seluruh modul konten siap (16 pertemuan)
                </h2>
                <p className={styles.statusDesc}>
                  Draf materi, resource, dan tugas untuk seluruh 16 minggu telah disusun oleh Agent AI. Anda dapat meninjau modul per minggu atau mempublikasikannya ke Moodle ITK.
                </p>
              </div>

              <div className={styles.statusActions}>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={handleStartBatchGenerate}
                >
                  Regenerate Semua
                </button>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() => onOpenModal('moodle-publish')}
                >
                  Publikasikan ke Moodle
                </button>
              </div>
            </div>
          ) : (
            <div className={styles.statusBanner}>
              <div className={styles.statusText}>
                <h2 className={styles.statusHeading}>
                  Rencana disetujui · Siap membuat konten mingguan
                </h2>
                <p className={styles.statusDesc}>
                  Gunakan tombol Auto Generate untuk menyusun modul materi 16 minggu sekaligus, atau klik modul tertentu untuk membuat per minggu.
                </p>
              </div>

              <div className={styles.statusActions}>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={handleStartBatchGenerate}
                >
                  ⚡ Auto Generate Konten Mingguan
                </button>
              </div>
            </div>
          )}

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
