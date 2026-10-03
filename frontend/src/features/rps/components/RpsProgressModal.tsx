import React, { useState, useEffect } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface RpsProgressModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

export const RpsProgressModal: React.FC<RpsProgressModalProps> = ({
  isOpen,
  onClose,
  onComplete,
}) => {
  const [progressStep, setProgressStep] = useState(2)

  useEffect(() => {
    if (!isOpen) return

    const timer1 = setTimeout(() => {
      setProgressStep(3)
    }, 700)

    const timer2 = setTimeout(() => {
      setProgressStep(4)
    }, 1500)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
    }
  }, [isOpen])

  const isDone = progressStep >= 4

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Menganalisis RPS"
      titleId="rps-progress-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            fontSize: '13px',
            lineHeight: 1.5,
          }}
        >
          <div style={{ color: '#059669', fontWeight: 500 }}>
            ✓ Dokumen berhasil diunggah
          </div>
          <div style={{ color: '#059669', fontWeight: 500 }}>
            ✓ Identitas mata kuliah ditemukan
          </div>
          <div
            style={{
              color: progressStep >= 4 ? '#059669' : progressStep === 3 ? '#2563EB' : '#94A3B8',
              fontWeight: progressStep >= 3 ? 500 : 400,
            }}
          >
            {progressStep >= 4 ? '✓' : progressStep === 3 ? '●' : '○'} Memetakan CPMK dan materi mingguan
          </div>
          <div
            style={{
              color: isDone ? '#059669' : progressStep === 3 ? '#2563EB' : '#94A3B8',
              fontWeight: isDone ? 500 : progressStep === 3 ? 600 : 400,
            }}
          >
            {isDone
              ? '✓ Hasil analisis selesai disiapkan'
              : progressStep === 3
              ? '● Menyiapkan hasil analisis'
              : '○ Menyiapkan hasil analisis'}
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '12px',
            marginTop: '8px',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              backgroundColor: '#FFFFFF',
              color: '#475569',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '10px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Lanjutkan di latar belakang
          </button>
          <button
            type="button"
            onClick={onComplete}
            disabled={!isDone}
            style={{
              backgroundColor: isDone ? '#1D4ED8' : '#94A3B8',
              color: '#FFFFFF',
              border: isDone ? '1px solid #1D4ED8' : '1px solid #94A3B8',
              borderRadius: '8px',
              padding: '10px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: isDone ? 'pointer' : 'not-allowed',
              boxShadow: isDone ? '0 0 0 2px rgba(37, 99, 235, 0.2)' : undefined,
              transition: 'all 0.2s ease',
            }}
          >
            {isDone ? 'Lihat Hasil Analisis' : 'Menganalisis Dokumen...'}
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
