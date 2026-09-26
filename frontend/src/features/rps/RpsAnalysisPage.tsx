import React, { useState } from 'react'
import type { AppPath } from '../../types/navigation'
import { RPS_ANALYSIS_DATA } from '../../data/courseData'
import styles from './RpsAnalysisPage.module.css'

interface RpsAnalysisPageProps {
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const RpsAnalysisPage: React.FC<RpsAnalysisPageProps> = ({
  onNavigate,
  onShowToast,
}) => {
  const [selectedWeek, setSelectedWeek] = useState(1)
  const [showFullDetails, setShowFullDetails] = useState(false)

  const activePlan =
    RPS_ANALYSIS_DATA.weeklyPlans.find((p) => p.weekNumber === selectedWeek) ||
    RPS_ANALYSIS_DATA.weeklyPlans[0]

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
        <button
          type="button"
          className={styles.breadcrumbLink}
          onClick={() => onNavigate('/course-plan')}
        >
          {RPS_ANALYSIS_DATA.courseName}
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Hasil Analisis RPS</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>Hasil Analisis RPS</h1>
          <p className={styles.pageSubtitle}>
            {RPS_ANALYSIS_DATA.courseName} · {RPS_ANALYSIS_DATA.courseCode} ·{' '}
            {RPS_ANALYSIS_DATA.sks} SKS · {RPS_ANALYSIS_DATA.totalWeeks} pertemuan
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() => onNavigate('/course-plan')}
          >
            Kembali ke Course Plan
          </button>
        </div>
      </div>

      {/* 1. BAGIAN ATAS: INFORMASI UMUM */}
      <section className={styles.generalInfoCard}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>Informasi Umum</h2>
          <span className={styles.badgeVerified}>
            ✓ {RPS_ANALYSIS_DATA.fileSize}
          </span>
        </div>

        {/* Metadata Grid */}
        <div className={styles.metaGrid}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Mata Kuliah</span>
            <span className={styles.metaValue}>{RPS_ANALYSIS_DATA.courseName}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Kode MK / Bobot</span>
            <span className={styles.metaValue}>
              {RPS_ANALYSIS_DATA.courseCode} · {RPS_ANALYSIS_DATA.sks} SKS
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Semester</span>
            <span className={styles.metaValue}>{RPS_ANALYSIS_DATA.semester}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Program Studi</span>
            <span className={styles.metaValue}>
              {RPS_ANALYSIS_DATA.programStudi || 'Informatika · ITK'}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Dosen Pengampu</span>
            <span className={styles.metaValue}>
              {RPS_ANALYSIS_DATA.dosenPengampu || 'Ramadhan Paninggalih S.Si., M.Si., M.Sc.'}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Koordinator Prodi</span>
            <span className={styles.metaValue}>
              {RPS_ANALYSIS_DATA.koordinatorProdi || 'Nisa Rizqiya Fadhliana, S.Kom., M.T.'}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Tanggal Penyusunan</span>
            <span className={styles.metaValue}>
              {RPS_ANALYSIS_DATA.tanggalPenyusunan || '16 Juli 2023'}
            </span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Dokumen Sumber</span>
            <span
              className={styles.metaValue}
              style={{
                color: '#1D4ED8',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
              onClick={() =>
                onShowToast?.(
                  `Membuka dokumen ${RPS_ANALYSIS_DATA.fileName}...`,
                  'info'
                )
              }
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onShowToast?.(
                    `Membuka dokumen ${RPS_ANALYSIS_DATA.fileName}...`,
                    'info'
                  )
                }
              }}
            >
              {RPS_ANALYSIS_DATA.fileName}
            </span>
          </div>
        </div>

        {/* Deskripsi Singkat MK */}
        {RPS_ANALYSIS_DATA.deskripsiSingkat && (
          <div className={styles.infoSection}>
            <h3 className={styles.sectionTitle}>Deskripsi Singkat Mata Kuliah</h3>
            <p className={styles.sectionContent}>
              {RPS_ANALYSIS_DATA.deskripsiSingkat}
            </p>
          </div>
        )}

        {/* Capaian Pembelajaran Lulusan (CPL) */}
        <div className={styles.infoSection}>
          <h3 className={styles.sectionTitle}>
            Capaian Pembelajaran Lulusan (CPL) yang Dititipkan
          </h3>
          <ul className={styles.cplList}>
            {RPS_ANALYSIS_DATA.targetCpl.map((cpl, idx) => (
              <li key={idx} className={styles.cplItem}>
                {cpl}
              </li>
            ))}
          </ul>
        </div>

        {/* Toggleable CPMK list */}
        {RPS_ANALYSIS_DATA.cpmkList && (
          <div className={styles.infoSection}>
            <button
              type="button"
              className={styles.toggleDetailsBtn}
              onClick={() => setShowFullDetails((prev) => !prev)}
            >
              {showFullDetails ? '▴ Sembunyikan' : '▾ Lihat'}{' '}
              Capaian Pembelajaran Mata Kuliah (CPMK · {RPS_ANALYSIS_DATA.cpmkCount} Butir)
            </button>

            {showFullDetails && (
              <ul className={styles.cplList} style={{ marginTop: '8px' }}>
                {RPS_ANALYSIS_DATA.cpmkList.map((cpmk, idx) => (
                  <li key={idx} className={styles.cplItem}>
                    {cpmk}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* 2. BAGIAN BAWAH: RENCANA MATERI */}
      <section className={styles.plansContainer}>
        <div className={styles.plansHeader}>
          <h2 className={styles.plansTitle}>Rencana Materi Perkuliahan</h2>
          <p className={styles.plansSubtitle}>
            Pilih minggu perkuliahan di bawah untuk melihat rincian Sub-CPMK dan Bahan Kajian
          </p>
        </div>

        {/* Horizontal Scroll Week Tabs (Minggu 1 s.d. Minggu 16) */}
        <div className={styles.weekScrollWrapper}>
          <div className={styles.weekScrollContainer} role="tablist" aria-label="Navigasi Minggu Perkuliahan">
            {RPS_ANALYSIS_DATA.weeklyPlans.map((plan) => {
              const isActive = plan.weekNumber === selectedWeek
              return (
                <button
                  key={plan.weekNumber}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={isActive ? styles.weekTabActive : styles.weekTab}
                  onClick={() => setSelectedWeek(plan.weekNumber)}
                >
                  Minggu {plan.weekNumber}
                </button>
              )
            })}
          </div>
        </div>

        {/* Sub-tab Bar */}
        <div className={styles.subTabBar}>
          <div className={styles.subTabActive}>Rencana Materi</div>
        </div>

        {/* Active Week Plan Card (Only Sub-CPMK and Bahan Kajian) */}
        <div className={styles.planCard}>
          <div className={styles.planCardHeader}>
            <span className={styles.planWeekBadge}>
              Pertemuan {selectedWeek < 10 ? `0${selectedWeek}` : selectedWeek}
            </span>
            <span style={{ fontSize: '13px', color: '#64748B' }}>
              3 SKS · {RPS_ANALYSIS_DATA.courseName}
            </span>
          </div>

          {/* Sub-CPMK */}
          <div className={styles.planItemBlock}>
            <h3 className={styles.planItemLabel}>Sub-CPMK</h3>
            <div className={styles.planSubCpmkContent}>
              {activePlan.subCpmk}
            </div>
          </div>

          {/* Bahan Kajian */}
          <div className={styles.planItemBlock}>
            <h3 className={styles.planItemLabel}>Bahan Kajian</h3>
            <ul className={styles.bahanKajianList}>
              {activePlan.bahanKajian.map((item, idx) => (
                <li key={idx} className={styles.bahanKajianItem}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  )
}
