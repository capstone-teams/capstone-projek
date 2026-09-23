import React from 'react'
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

      {/* Content Layout */}
      <div className={styles.splitLayout}>
        <div className={styles.splitMain}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Informasi Akademik</h3>
            <div className={styles.cardContent}>
              {`${RPS_ANALYSIS_DATA.courseName} · ${RPS_ANALYSIS_DATA.courseCode} · ${RPS_ANALYSIS_DATA.sks} SKS
${RPS_ANALYSIS_DATA.semester} · ${RPS_ANALYSIS_DATA.totalWeeks} pertemuan

Capaian pembelajaran
Menganalisis ancaman dan menerapkan prinsip keamanan pada sistem informasi.

Metode & evaluasi
Studi kasus, praktikum, tugas proyek, UTS, dan UAS.`}
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Distribusi Materi</h3>
            <div
              className={styles.cardContent}
              style={{ fontFamily: 'monospace', fontSize: '13px' }}
            >
              {`Minggu 1–4     Dasar keamanan, ancaman, dan rekognisi
Minggu 5–7     Keamanan web, malware, dan akses
Minggu 8         Ujian Tengah Semester
Minggu 9–15   Keamanan sistem, kasus, dan proyek
Minggu 16       Ujian Akhir Semester`}
            </div>
          </div>
        </div>

        <div className={styles.splitSide}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>RPS berhasil dianalisis</h3>
            <div className={styles.cardContent}>
              {`${RPS_ANALYSIS_DATA.fileName}

Identitas & capaian: halaman 1–2
Rencana mingguan: halaman 3–7
Evaluasi & referensi: halaman 8

Sumber utama: dokumen RPS.`}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                type="button"
                className={styles.btnSecondary}
                style={{ width: '100%' }}
                onClick={() =>
                  onShowToast?.(
                    `Membuka dokumen ${RPS_ANALYSIS_DATA.fileName}...`,
                    'info'
                  )
                }
              >
                Lihat Dokumen RPS
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
