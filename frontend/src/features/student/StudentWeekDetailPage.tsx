import React from 'react'
import type { AppPath } from '../../types/navigation'
import styles from './Student.module.css'

interface StudentWeekDetailPageProps {
  weekNumber?: number
  onSelectMaterial?: (documentId: string) => void
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const StudentWeekDetailPage: React.FC<StudentWeekDetailPageProps> = ({
  weekNumber = 3,
  onSelectMaterial,
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
          Aljabar Linear dan Geometri
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Minggu 03</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>
            Pertemuan 03 · Determinan & Invers Matriks
          </h1>
          <p className={styles.pageSubtitle}>
            Aljabar Linear dan Geometri · Materi dan aktivitas pembelajaran
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
Menghitung determinan dengan reduksi baris elementer dan ekspansi kofaktor, serta menentukan invers matriks non-singular.

Determinan & Invers Matriks (OBE & Kofaktor)
Pelajari sifat-sifat determinan, operasi baris elementer, dan matriks adjoint untuk mencari invers matriks.`}
            </div>

            <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() => {
                  const docId = weekNumber === 2 ? 'doc-week2-pdf' : 'doc-week3-pdf'
                  onSelectMaterial?.(docId)
                  onNavigate('/material-view')
                }}
              >
                Buka Modul Materi Lengkap
              </button>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() =>
                  onShowToast?.(
                    'Membuka Materi Minggu 03 di Moodle ITK (Tab Baru)...',
                    'info'
                  )
                }
              >
                Buka di Moodle
              </button>
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Resource Pembelajaran</h3>
            <div className={styles.cardContent}>
              {`Modul Determinan & Invers Matriks
Dokumen pendamping materi perkuliahan minggu ke-3.`}
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() => {
                  const docId = weekNumber === 2 ? 'doc-week2-ppt' : 'doc-week3-ppt'
                  onSelectMaterial?.(docId)
                  onNavigate('/material-view')
                }}
              >
                Lihat Slide Perkuliahan
              </button>
            </div>
          </div>
        </div>

        <div className={styles.splitSide}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Tugas Minggu Ini</h3>
            <div className={styles.cardContent}>
              {`Latihan invers matriks OBE
Gunakan metode reduksi baris elementer pada soal studi kasus yang diberikan dosen.

Batas pengumpulan
27 September 2026 · 23.59

Tersedia di Moodle`}
            </div>

            <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button
                type="button"
                className={styles.btnPrimary}
                style={{ width: '100%' }}
                onClick={() => {
                  const docId = weekNumber === 2 ? 'doc-week2-task' : 'doc-week3-task'
                  onSelectMaterial?.(docId)
                  onNavigate('/material-view')
                }}
              >
                Buka Lembar Latihan Tugas
              </button>
              <button
                type="button"
                className={styles.btnSecondary}
                style={{ width: '100%' }}
                onClick={() =>
                  onShowToast?.(
                    'Membuka Halaman Pengumpulan Tugas di Moodle ITK...',
                    'info'
                  )
                }
              >
                Kumpul ke Moodle
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
