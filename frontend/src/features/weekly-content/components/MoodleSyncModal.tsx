import React, { useState, useEffect } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface MoodleSyncModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

export const MoodleSyncModal: React.FC<MoodleSyncModalProps> = ({
  isOpen,
  onClose,
  onComplete,
}) => {
  const [progressStep, setProgressStep] = useState(2)

  useEffect(() => {
    if (!isOpen) return

    const timer = setTimeout(() => {
      setProgressStep(3)
    }, 1000)

    return () => clearTimeout(timer)
  }, [isOpen])

  const isDone = progressStep >= 3

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Mengirim dan memeriksa Moodle"
      titleId="moodle-sync-title"
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
            ✓ Section minggu 03 tersedia
          </div>
          <div style={{ color: '#059669', fontWeight: 500 }}>
            ✓ Materi dan resource berhasil dikirim
          </div>
          <div style={{ color: '#059669', fontWeight: 500 }}>
            ✓ Tugas berhasil dikirim
          </div>
          <div
            style={{
              color: isDone ? '#059669' : '#2563EB',
              fontWeight: isDone ? 500 : 600,
            }}
          >
            {isDone ? '✓' : '●'} Memeriksa kembali akses konten di Moodle
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
            {isDone ? 'Lihat Hasil Moodle' : 'Menyinkronkan ke Moodle...'}
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
