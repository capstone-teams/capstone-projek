import React, { useState, useEffect } from 'react'
import type { AppPath, ModalType } from '../../types/navigation'
import type { WeeklyContentStage } from '../../types/course'
import styles from './WeekDetailPage.module.css'

interface WeekDetailPageProps {
  stage: WeeklyContentStage
  weekNumber?: number
  onStageChange?: (newStage: WeeklyContentStage) => void
  onSelectMaterial?: (documentId: string) => void
  onNavigate: (path: AppPath) => void
  onOpenModal: (modal: ModalType) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

const MatrixConceptDiagram: React.FC = () => (
  <svg
    viewBox="0 0 680 170"
    style={{ width: '100%', maxWidth: '640px', height: 'auto' }}
    role="img"
    aria-label="Diagram Transformasi Invers Matriks Menggunakan Eliminasi Gauss-Jordan"
  >
    <defs>
      <marker
        id="arrow"
        viewBox="0 0 10 10"
        refX="5"
        refY="5"
        markerWidth="6"
        markerHeight="6"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563EB" />
      </marker>
    </defs>

    {/* Box A: [A | I] */}
    <rect
      x="20"
      y="20"
      width="210"
      height="125"
      rx="8"
      fill="#FFFFFF"
      stroke="#CBD5E1"
      strokeWidth="1.5"
    />
    <text x="125" y="48" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1E293B">
      Matriks Teraugmentasi
    </text>
    <rect x="35" y="60" width="180" height="55" rx="6" fill="#F8FAFC" stroke="#E2E8F0" />
    <text
      x="125"
      y="94"
      textAnchor="middle"
      fontSize="16"
      fontWeight="700"
      fill="#2563EB"
      fontFamily="monospace"
    >
      [ A | I₃ ]
    </text>
    <text x="125" y="132" textAnchor="middle" fontSize="11" fill="#64748B">
      Kondisi Awal (Matriks Bujursangkar)
    </text>

    {/* Arrow OBE */}
    <line
      x1="245"
      y1="82"
      x2="415"
      y2="82"
      stroke="#2563EB"
      strokeWidth="2.5"
      markerEnd="url(#arrow)"
    />
    <text x="330" y="68" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1D4ED8">
      Operasi Baris Elementer (OBE)
    </text>
    <text x="330" y="105" textAnchor="middle" fontSize="11" fill="#64748B">
      Eliminasi Gauss-Jordan
    </text>

    {/* Box B: [I | A^-1] */}
    <rect
      x="430"
      y="20"
      width="220"
      height="125"
      rx="8"
      fill="#FFFFFF"
      stroke="#93C5FD"
      strokeWidth="2"
    />
    <text x="540" y="48" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1E293B">
      Bentuk Eselon Tereduksi
    </text>
    <rect x="445" y="60" width="190" height="55" rx="6" fill="#EFF6FF" stroke="#BFDBFE" />
    <text
      x="540"
      y="94"
      textAnchor="middle"
      fontSize="16"
      fontWeight="700"
      fill="#1D4ED8"
      fontFamily="monospace"
    >
      [ I₃ | A⁻¹ ]
    </text>
    <text x="540" y="132" textAnchor="middle" fontSize="11" fontWeight="600" fill="#059669">
      ✓ Matriks Invers Terverifikasi
    </text>
  </svg>
)

export const WeekDetailPage: React.FC<WeekDetailPageProps> = ({
  stage,
  weekNumber = 3,
  onStageChange,
  onSelectMaterial,
  onNavigate,
  onOpenModal,
  onShowToast,
}) => {
  const [activeWeekOverride, setActiveWeekOverride] = useState<number | null>(null)
  const [prevWeekNumber, setPrevWeekNumber] = useState(weekNumber)

  if (prevWeekNumber !== weekNumber) {
    setPrevWeekNumber(weekNumber)
    setActiveWeekOverride(null)
  }

  const activeWeek = activeWeekOverride ?? weekNumber
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStep, setGenerationStep] = useState(1)
  const [progressPercent, setProgressPercent] = useState(25)

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
      onStageChange?.('review')
      onShowToast?.(
        `Draft materi dan tugas Minggu 0${activeWeek} berhasil disusun oleh Agent AI berdasarkan profil dosen & RPS.`,
        'success'
      )
    }, 2500)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
    }
  }, [isGenerating, onStageChange, onShowToast, activeWeek])

  const handleStartGenerate = () => {
    setGenerationStep(1)
    setProgressPercent(25)
    setIsGenerating(true)
  }

  const handleOpenDoc = (docId: string) => {
    onSelectMaterial?.(docId)
    onNavigate('/material-view')
  }

  const formattedWeek = activeWeek < 10 ? `0${activeWeek}` : activeWeek

  return (
    <div className={styles.container}>
      {/* Top Header with Breadcrumbs & Reference Style Switcher */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
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
          <span className={styles.breadcrumbCurrent}>Detail Minggu {formattedWeek}</span>
        </div>

        {/* Style Reference Switcher (Minggu 02 vs Minggu 03) */}
        <div className={styles.weekSwitcher}>
          <span style={{ fontSize: '11px', color: '#64748B', paddingLeft: '8px', fontWeight: 600 }}>
            Contoh Tampilan:
          </span>
          <button
            type="button"
            className={activeWeek === 2 ? `${styles.weekSwitcherBtn} ${styles.weekSwitcherBtnActive}` : styles.weekSwitcherBtn}
            onClick={() => setActiveWeekOverride(2)}
          >
            Minggu 02 · Gaya LMS ITK
          </button>
          <button
            type="button"
            className={activeWeek === 3 ? `${styles.weekSwitcherBtn} ${styles.weekSwitcherBtnActive}` : styles.weekSwitcherBtn}
            onClick={() => setActiveWeekOverride(3)}
          >
            Minggu 03 · Modern Visual
          </button>
        </div>
      </div>

      {/* Page Heading */}
      <div className={styles.pageHeading}>
        <div className={styles.headingText}>
          <h1 className={styles.pageTitle}>
            {activeWeek === 2
              ? 'Pertemuan 02 · Operasi Matriks & SPL'
              : 'Pertemuan 03 · Determinan & Invers Matriks'}
          </h1>
          <p className={styles.pageSubtitle}>
            {activeWeek === 2
              ? 'Aljabar Linear dan Geometri · IF201405 · 3 SKS · Gaya Klasik LMS ITK'
              : 'Aljabar Linear dan Geometri · IF201405 · 3 SKS · Gaya Modern Visual'}
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
              {activeWeek === 2
                ? `Tujuan:\nMahasiswa mampu melakukan operasi matriks (penjumlahan, pengurangan, perkalian matriks), serta memodelkan sistem persamaan linear menggunakan matriks augmented.\n\nAktivitas:\nMateri perkuliahan interaktif, latihan perkalian matriks, dan pemodelan SPL.`
                : `Tujuan:\nMenentukan determinan dan invers matriks menggunakan Operasi Baris Elementer (OBE) dan kofaktor.\n\nAktivitas:\nMateri perkuliahan, latihan penerapan OBE, perhitungan kofaktor, dan latihan soal mandiri.`}
            </div>
          </div>

          <div className={styles.emptyCard}>
            <h2 className={styles.emptyTitle}>Konten belum tersedia</h2>
            <p className={styles.emptyDesc}>
              Generate draf materi pembelajaran, resource, dan tugas untuk minggu ini dengan bantuan Agentic AI.
            </p>

            {!isGenerating ? (
              <button
                type="button"
                className={styles.btnPrimary}
                style={{ width: '200px', height: '44px' }}
                onClick={handleStartGenerate}
              >
                Generate Konten
              </button>
            ) : (
              <div className={styles.agentMonitoringCard}>
                <div className={styles.monitoringHeader}>
                  <span className={styles.pulseDot} />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <h4 className={styles.monitoringTitle}>
                      Agent AI sedang menyusun konten pertemuan {formattedWeek}...
                    </h4>
                    <span className={styles.monitoringSubtitle}>
                      Menerapkan preferensi profil dosen & silabus RPS
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
                    {generationStep > 1 ? '✓' : generationStep === 1 ? '●' : '○'} Mengambil topik silabus: {activeWeek === 2 ? 'Operasi Matriks & SPL' : 'Determinan & Invers Matriks'}
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
                    {generationStep > 2 ? '✓' : generationStep === 2 ? '●' : '○'} Menerapkan preferensi dosen (studi kasus & komputasi)
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
                    {generationStep > 3 ? '✓' : generationStep === 3 ? '●' : '○'} Menyusun modul materi, resource bacaan, dan tugas
                  </div>
                  <div
                    className={
                      generationStep >= 4 ? styles.stepDone : styles.stepPending
                    }
                  >
                    {generationStep >= 4
                      ? '✓ Finalisasi draf konten pembelajaran tervalidasi'
                      : '○ Memvalidasi draf konten pembelajaran'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Stage: Review & Synced */}
      {(stage === 'review' || stage === 'synced') && (
        <div className={styles.splitLayout}>
          <div className={styles.splitMain}>
            {/* CONTOH 1: MINGGU 02 (Gaya Klasik LMS ITK Persis Screenshot) */}
            {activeWeek === 2 ? (
              <div className={styles.lmsTopicCard}>
                {/* Sub-CPMK */}
                <div className={styles.subCpmkBlock}>
                  <div className={styles.subCpmkTitle}>Sub-CPMK:</div>
                  <div className={styles.subCpmkText}>
                    Mahasiswa mampu melakukan operasi matriks, determinan, dan invers matriks.
                  </div>
                </div>

                {/* Bahan Kajian */}
                <div className={styles.subCpmkBlock}>
                  <div className={styles.bahanKajianTitle}>Bahan Kajian:</div>
                  <ul className={styles.bahanKajianList}>
                    <li>Operasi penjumlahan dan pengurangan pada matriks</li>
                    <li>Operasi perkalian pada matriks</li>
                    <li>Sifat-sifat operasi matriks dan transpose matriks</li>
                    <li>Sistem Persamaan Linear (SPL) dan bentuk matriks teraugmentasi</li>
                    <li>Operasi Baris Elementer (OBE) dasar</li>
                  </ul>
                </div>

                {/* Instructor Note as in Screenshot */}
                <div className={styles.lmsInstructorNote}>
                  Silahkan bapak/ibu dosen pengampu menambahkan file materi, tugas ataupun kuis.
                </div>

                {/* Clickable File Items (LMS ITK Moodle Row Style) */}
                <div className={styles.lmsFileList}>
                  <div
                    className={styles.lmsFileCard}
                    onClick={() => handleOpenDoc('doc-week2-pdf')}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleOpenDoc('doc-week2-pdf')
                      }
                    }}
                  >
                    <div className={styles.lmsFileInfo}>
                      <div className={styles.fileIconPdf}>PDF</div>
                      <div>
                        <div className={styles.lmsFileTitle}>Pengantar & Operasi Dasar Matriks.pdf</div>
                        <div className={styles.lmsFileMeta}>Dokumen PDF · 2.8 MB · Klik untuk membuka isi modul materi</div>
                      </div>
                    </div>
                    <span className={styles.lmsActionArrow}>Buka Dokumen →</span>
                  </div>

                  <div
                    className={styles.lmsFileCard}
                    onClick={() => handleOpenDoc('doc-week2-ppt')}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleOpenDoc('doc-week2-ppt')
                      }
                    }}
                  >
                    <div className={styles.lmsFileInfo}>
                      <div className={styles.fileIconPpt}>PPT</div>
                      <div>
                        <div className={styles.lmsFileTitle}>Slide Perkuliahan: Sistem Persamaan Linear.pptx</div>
                        <div className={styles.lmsFileMeta}>Presentasi Slide PPT · 4.5 MB · Klik untuk membaca materi kuliah</div>
                      </div>
                    </div>
                    <span className={styles.lmsActionArrow}>Buka Dokumen →</span>
                  </div>

                  <div
                    className={styles.lmsFileCard}
                    onClick={() => handleOpenDoc('doc-week2-task')}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleOpenDoc('doc-week2-task')
                      }
                    }}
                  >
                    <div className={styles.lmsFileInfo}>
                      <div className={styles.fileIconTask}>TUGAS</div>
                      <div>
                        <div className={styles.lmsFileTitle}>Latihan Mandiri 01: Eliminasi Gauss-Jordan.pdf</div>
                        <div className={styles.lmsFileMeta}>Penugasan Praktik · 1.2 MB · Tenggat pengumpulan: Minggu Depan</div>
                      </div>
                    </div>
                    <span className={styles.lmsActionArrow}>Lihat Tugas →</span>
                  </div>
                </div>
              </div>
            ) : (
              /* CONTOH 2: MINGGU 03 (Gaya Modern Visual dengan Gambar & Diagram) */
              <>
                {/* Modern Header Overview Card */}
                <div className={styles.modernHeaderCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className={styles.badgeSubCpmk}>Sub-CPMK 2 · Capaian Utama</span>
                    <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>3 SKS · Teori & Praktikum</span>
                  </div>

                  <div>
                    <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>
                      Determinan Matriks, Ekspansi Kofaktor & Invers Matriks
                    </h3>
                    <p style={{ fontSize: '14px', color: '#334155', lineHeight: 1.6, margin: 0 }}>
                      Mahasiswa mampu menentukan nilai determinan matriks menggunakan Operasi Baris Elementer (OBE) dan ekspansi kofaktor, serta menghitung invers matriks non-singular.
                    </p>
                  </div>

                  <div>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#475569' }}>Bahan Kajian Terpetakan:</span>
                    <div className={styles.chipsContainer}>
                      <span className={styles.chipItem}>• Determinan dengan Reduksi Baris (OBE)</span>
                      <span className={styles.chipItem}>• Ekspansi Kofaktor Laplace</span>
                      <span className={styles.chipItem}>• Matriks Adjoint (Adj A)</span>
                      <span className={styles.chipItem}>• Algoritma Invers [A | I] → [I | A⁻¹]</span>
                    </div>
                  </div>
                </div>

                {/* Concept Diagram Card (Gambar & Ilustrasi Konsep) */}
                <div className={styles.conceptDiagramCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 className={styles.cardTitle}>Diagram Konsep Matematis: Transformasi Invers Matriks</h3>
                    <span style={{ fontSize: '11px', color: '#2563EB', fontWeight: 600, backgroundColor: '#EFF6FF', padding: '3px 8px', borderRadius: '4px' }}>
                      Visualisasi Aljabar
                    </span>
                  </div>

                  <div className={styles.diagramContainer}>
                    <MatrixConceptDiagram />
                    <div className={styles.diagramCaption}>
                      Gambar 3.1: Skema transformasi reduksi baris Gauss-Jordan dari matriks teraugmentasi [A | I] menuju bentuk eselon tereduksi [I | A⁻¹].
                    </div>
                  </div>
                </div>

                {/* 2-Column Rich Module Grid */}
                <div className={styles.richModuleGrid}>
                  {/* Module 1: PDF Modul Teori */}
                  <div className={styles.card}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#1D4ED8', backgroundColor: '#EFF6FF', padding: '3px 8px', borderRadius: '4px' }}>
                        MODUL TEORI LENGKAP
                      </span>
                      <span style={{ fontSize: '12px', color: '#64748B' }}>⏱️ 35 Menit Baca</span>
                    </div>

                    <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A', marginTop: '6px' }}>
                      Modul Lengkap: Determinan & Invers Matriks.pdf
                    </h4>

                    <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.6 }}>
                      Membahas konsep nilai determinan, sifat aljabar determinan, rumus ekspansi kofaktor, dan invers adjoin.
                    </p>

                    <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
                      <button
                        type="button"
                        className={styles.btnPrimary}
                        style={{ width: '100%' }}
                        onClick={() => handleOpenDoc('doc-week3-pdf')}
                      >
                        Buka Materi Lengkap →
                      </button>
                    </div>
                  </div>

                  {/* Module 2: Slides & Assignment */}
                  <div className={styles.card}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#C2410C', backgroundColor: '#FFF7ED', padding: '3px 8px', borderRadius: '4px' }}>
                        SLIDE & PENUGASAN
                      </span>
                      <span style={{ fontSize: '12px', color: '#64748B' }}>2 Berkas Siap</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
                      <div
                        onClick={() => handleOpenDoc('doc-week3-ppt')}
                        style={{ padding: '8px 12px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      >
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B' }}>Slide Perkuliahan (PPT)</div>
                          <div style={{ fontSize: '11px', color: '#64748B' }}>5.1 MB · 24 Slide Presentasi</div>
                        </div>
                        <span style={{ fontSize: '12px', color: '#2563EB', fontWeight: 600 }}>Buka →</span>
                      </div>

                      <div
                        onClick={() => handleOpenDoc('doc-week3-task')}
                        style={{ padding: '8px 12px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      >
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B' }}>Tugas 02: Invers Matriks OBE</div>
                          <div style={{ fontSize: '11px', color: '#64748B' }}>1.5 MB · Tenggat 2 September 2026</div>
                        </div>
                        <span style={{ fontSize: '12px', color: '#2563EB', fontWeight: 600 }}>Buka →</span>
                      </div>
                    </div>

                    <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
                      <button
                        type="button"
                        className={styles.btnSecondary}
                        style={{ width: '100%' }}
                        onClick={() => handleOpenDoc('doc-week3-task')}
                      >
                        Lihat Rincian Tugas →
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Right Sidebar: Dosen Review Actions */}
          <div className={styles.splitSide}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Status Publikasi Moodle</h3>
              <div className={styles.cardContent}>
                {stage === 'synced'
                  ? `✓ Modul materi dan tugas telah tersinkronisasi secara otomatis ke server LMS Moodle ITK.`
                  : `Draf modul pertemuan Minggu 0${activeWeek} telah siap ditinjau. Anda dapat memeriksa isi materi sebelum mempublikasikan.`}
              </div>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  marginTop: '16px',
                }}
              >
                {stage === 'review' && (
                  <>
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
                  </>
                )}

                {stage === 'synced' && (
                  <button
                    type="button"
                    className={styles.btnSecondary}
                    onClick={() =>
                      onShowToast?.(
                        `Membuka laman pertemuan Minggu 0${activeWeek} di Moodle ITK...`,
                        'info'
                      )
                    }
                  >
                    Buka di LMS Moodle ITK
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
