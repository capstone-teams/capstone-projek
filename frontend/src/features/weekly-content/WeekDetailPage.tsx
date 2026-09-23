import React from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { WeeklyContentStage } from '../../types/course'
import styles from './WeekDetailPage.module.css'

interface WeekDetailPageProps {
  stage: WeeklyContentStage
  onNavigate: (path: AppPath) => void
  onOpenModal: (modal: ModalType) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const WeekDetailPage: React.FC<WeekDetailPageProps> = ({
  stage,
  onNavigate,
  onOpenModal,
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
          Keamanan Siber
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>Detail Minggu 03</span>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>
            Pertemuan 03 · Rekognisi Jejak Digital
          </h1>
          <p className={styles.pageSubtitle}>
            {stage === 'empty'
              ? 'Keamanan Siber · Belum ada konten pembelajaran'
              : stage === 'review'
              ? 'Keamanan Siber · Draft konten siap ditinjau'
              : 'Keamanan Siber · Konten disetujui & sinkron Moodle ITK'}
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

      {/* Stage: Empty */}
      {stage === 'empty' && (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Tujuan dan rencana minggu</h3>
            <div className={styles.cardContent}>
              {`Tujuan
Mengidentifikasi jejak digital dan teknik rekognisi pasif/aktif.

Aktivitas
Materi, panduan studi kasus, dan tugas simulasi.`}
            </div>
          </div>

          <div className={styles.emptyCard}>
            <h2 className={styles.emptyTitle}>Konten belum tersedia</h2>
            <p className={styles.emptyDesc}>
              Generate draf materi pembelajaran, resource, dan tugas untuk minggu ini dengan bantuan Agentic AI.
            </p>
            <button
              type="button"
              className={styles.btnPrimary}
              style={{ width: '200px', height: '44px' }}
              onClick={() => onOpenModal('generate-content')}
            >
              Generate Konten
            </button>
          </div>
        </>
      )}

      {stage === 'review' && (
        <div className={styles.splitLayout}>
          <div className={styles.splitMain}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Materi Pembelajaran</h3>
              <div className={styles.cardContent}>
                {`Rekognisi Jejak Digital

Tujuan pembelajaran
Mengidentifikasi jejak digital dan menjelaskan teknik rekognisi pada lingkungan yang diizinkan.

Materi membahas rekognisi pasif, rekognisi aktif, dan dokumentasi hasil pengamatan.

Konten draf versi 1 · Disusun oleh Agent`}
              </div>
            </div>

            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Resource dan Aktivitas</h3>
              <div className={styles.cardContent}>
                {`Resource: Panduan rekognisi dan studi kasus simulasi (PDF)
Tugas: Analisis jejak digital pada kasus simulasi
Quiz: Tidak diaktifkan`}
              </div>

              <div style={{ marginTop: '12px' }}>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() =>
                    onShowToast?.(
                      'Pratinjau Tugas: Analisis Jejak Digital...',
                      'info'
                    )
                  }
                >
                  Pratinjau Tugas
                </button>
              </div>
            </div>
          </div>

          <div className={styles.splitSide}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Review Dosen</h3>
              <div className={styles.cardContent}>
                {`Draf siap ditinjau.

Periksa kesesuaian materi, resource, dan tugas sebelum mengirim ke Moodle.`}
              </div>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  marginTop: '16px',
                }}
              >
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() => onOpenModal('content-revision')}
                >
                  Minta Revisi
                </button>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() => onOpenModal('moodle-publish')}
                >
                  Setujui & Publikasikan ke Moodle
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {stage === 'synced' && (
        <div className={styles.splitLayout}>
          <div className={styles.splitMain}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Materi Pembelajaran</h3>
              <div className={styles.cardContent}>
                {`Rekognisi Jejak Digital

Tujuan pembelajaran
Mengidentifikasi jejak digital dan menjelaskan teknik rekognisi pada lingkungan yang diizinkan.

Materi membahas rekognisi pasif, rekognisi aktif, dan dokumentasi hasil pengamatan.

Konten versi 1 · Disetujui dosen & Tersinkronisasi`}
              </div>

              <div style={{ marginTop: '12px' }}>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() =>
                    onShowToast?.(
                      'Membuka Materi di Moodle ITK (Tab Baru)...',
                      'info'
                    )
                  }
                >
                  Buka Materi di Moodle
                </button>
              </div>
            </div>

            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Aktivitas Pembelajaran</h3>
              <div
                className={styles.cardContent}
                style={{ fontFamily: 'monospace', fontSize: '13px' }}
              >
                {`Resource     Panduan rekognisi dan studi kasus
Tugas           Analisis jejak digital pada kasus simulasi
Quiz             Tidak diaktifkan`}
              </div>

              <div style={{ marginTop: '12px' }}>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() =>
                    onShowToast?.(
                      'Membuka Tugas di Moodle ITK (Tab Baru)...',
                      'info'
                    )
                  }
                >
                  Buka Tugas di Moodle
                </button>
              </div>
            </div>
          </div>

          <div className={styles.splitSide}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Status Moodle</h3>
              <div className={styles.cardContent}>
                <div
                  style={{
                    color: '#059669',
                    fontWeight: 700,
                    marginBottom: '8px',
                  }}
                >
                  Terverifikasi
                </div>
                {`✓  Section pertemuan 3 tersedia
✓  Materi sesuai
✓  Resource sesuai
✓  Tugas sesuai

Target: Keamanan Siber — Kelas A
Hasil dibaca ulang dari Moodle.`}
              </div>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  marginTop: '16px',
                }}
              >
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() => onOpenModal('moodle-sync')}
                >
                  Lihat Proses Sinkronisasi
                </button>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() =>
                    onShowToast?.(
                      'Membuka Course Keamanan Siber di Moodle ITK...',
                      'info'
                    )
                  }
                >
                  Buka Course Moodle
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
