import React from 'react'
import type { AppPath } from '../../types/navigation'
import { WEEKLY_MATERIALS_DATA } from '../../data/courseData'
import styles from './MaterialViewPage.module.css'

interface MaterialViewPageProps {
  documentId?: string
  weekNumber?: number
  onNavigate: (path: AppPath) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const MaterialViewPage: React.FC<MaterialViewPageProps> = ({
  documentId = 'doc-week3-pdf',
  weekNumber = 3,
  onNavigate,
  onShowToast,
}) => {
  const doc =
    WEEKLY_MATERIALS_DATA[documentId] ||
    (weekNumber === 2
      ? WEEKLY_MATERIALS_DATA['doc-week2-pdf']
      : WEEKLY_MATERIALS_DATA['doc-week3-pdf'])

  const formattedWeek = doc.weekNumber < 10 ? `0${doc.weekNumber}` : doc.weekNumber

  const getBadgeClass = (type: string) => {
    switch (type) {
      case 'ppt':
        return styles.badgeTypePpt
      case 'assignment':
        return styles.badgeTypeTask
      default:
        return styles.badgeTypePdf
    }
  }

  const handleDownload = () => {
    onShowToast?.(`Mengunduh berkas ${doc.title}...`, 'success')
  }

  const handleCopySummary = () => {
    onShowToast?.('Ringkasan materi berhasil disalin ke papan klip.', 'info')
  }

  return (
    <div className={styles.container}>
      {/* Breadcrumb Hierarchy */}
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
          Aljabar Linear dan Geometri
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <button
          type="button"
          className={styles.breadcrumbLink}
          onClick={() => onNavigate('/weekly-content')}
        >
          Detail Minggu {formattedWeek}
        </button>
        <span className={styles.breadcrumbSeparator}>/</span>
        <span className={styles.breadcrumbCurrent}>{doc.title}</span>
      </div>

      {/* Header Actions */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>{doc.title}</h1>
          <div className={styles.pageMeta}>
            <span className={getBadgeClass(doc.fileType)}>
              {doc.fileType.toUpperCase()}
            </span>
            <span>Ukuran: {doc.fileSize}</span>
            <span>·</span>
            <span>Diperbarui: {doc.uploadedDate}</span>
            <span>·</span>
            <span>Pertemuan Minggu {formattedWeek}</span>
          </div>
        </div>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={() => onNavigate('/weekly-content')}
          >
            ← Kembali ke Detail Minggu
          </button>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={handleDownload}
          >
            📥 Unduh Berkas
          </button>
        </div>
      </div>

      {/* Reader Canvas / Document Viewer */}
      <article className={styles.readerCanvas}>
        <div className={styles.docBanner}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#1D4ED8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Modul Pembelajaran · Institut Teknologi Kalimantan
            </span>
            {doc.estimatedTime && (
              <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 500 }}>
                {doc.estimatedTime}
              </span>
            )}
          </div>
          <h2 className={styles.docTitle}>{doc.title.replace(/\.[^/.]+$/, '')}</h2>
          <p className={styles.docDescription}>{doc.description}</p>
        </div>

        {/* Sub-CPMK Mapping */}
        <div className={styles.subCpmkBox}>
          <div className={styles.subCpmkLabel}>Kesesuaian Sub-CPMK RPS:</div>
          <div>{doc.subCpmkRef}</div>
        </div>

        {/* Sections Content */}
        {doc.sections.map((section, idx) => (
          <section key={idx} className={styles.docSection}>
            <h3 className={styles.sectionHeading}>{section.heading}</h3>
            <p className={styles.sectionContent}>{section.content}</p>

            {section.formula && (
              <div className={styles.formulaBox}>
                <code>{section.formula}</code>
              </div>
            )}
          </section>
        ))}

        {/* Exercise Prompt if available */}
        {doc.exercisePrompt && (
          <div className={styles.exerciseCard}>
            <div className={styles.exerciseTitle}>Latihan Mandiri & Evaluasi Pemahaman:</div>
            <p className={styles.exerciseText}>{doc.exercisePrompt}</p>
          </div>
        )}

        {/* Footer Actions */}
        <div className={styles.readerFooter}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={handleCopySummary}
          >
            📋 Salin Ringkasan Materi
          </button>

          <button
            type="button"
            className={styles.btnPrimary}
            onClick={() => onNavigate('/weekly-content')}
          >
            Selesai Membaca & Kembali
          </button>
        </div>
      </article>
    </div>
  )
}
