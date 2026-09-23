import React from 'react'
import type { AppPath } from '../../types/navigation'
import styles from './Student.module.css'

interface StudentWeekDetailPageProps {
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const StudentWeekDetailPage: React.FC<StudentWeekDetailPageProps> = ({
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
          onClick={() => onNavigate('/student/courses')}
        >
          Mata Kuliah
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <button
          type="button"
          className={styles.breadcrumbLink}
          onClick={() => onNavigate('/student/course')}
        >
          Keamanan Siber
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Minggu 03</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>
            Pertemuan 03 · Rekognisi Jejak Digital
          </h1>
          <p className={styles.pageSubtitle}>
            Keamanan Siber · Materi dan aktivitas pembelajaran
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() => onNavigate('/student/course')}
          >
            Kembali ke Mata Kuliah
          </button>
        </div>
      </div>

      {/* Content Layout */}
      <div className={styles.splitLayout}>
        <div className={styles.splitMain}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Materi Pembelajaran</h3>
            <div className={styles.cardContent}>
              {`Tujuan pembelajaran
Mengidentifikasi jejak digital dan menjelaskan teknik rekognisi pada lingkungan pengujian yang diizinkan.

Rekognisi Jejak Digital
Pelajari perbedaan rekognisi pasif dan aktif serta cara mendokumentasikan informasi pada studi kasus.`}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() =>
                  onShowToast?.(
                    'Membuka Materi Minggu 03 di Moodle ITK (Tab Baru)...',
                    'info'
                  )
                }
              >
                Baca Materi di Moodle
              </button>
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Resource Pembelajaran</h3>
            <div className={styles.cardContent}>
              {`Panduan rekognisi dan studi kasus
Dokumen pendamping materi pertemuan 3.`}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() =>
                  onShowToast?.(
                    'Membuka Dokumen Resource: Panduan Rekognisi...',
                    'info'
                  )
                }
              >
                Buka Resource
              </button>
            </div>
          </div>
        </div>

        <div className={styles.splitSide}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Tugas Minggu Ini</h3>
            <div className={styles.cardContent}>
              {`Analisis jejak digital
Gunakan kasus simulasi yang disediakan dosen.

Batas pengumpulan
27 September 2026 · 23.59

Tersedia di Moodle`}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                style={{ width: '100%' }}
                onClick={() =>
                  onShowToast?.(
                    'Membuka Halaman Pengumpulan Tugas di Moodle ITK...',
                    'info'
                  )
                }
              >
                Buka Tugas
              </button>
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Aktivitas Lainnya</h3>
            <div className={styles.cardContent}>
              {`Tidak ada quiz pada pertemuan ini.

Kembali ke overview untuk memilih pertemuan lainnya.`}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
