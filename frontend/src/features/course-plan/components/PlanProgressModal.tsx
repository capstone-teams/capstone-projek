import React, { useState, useEffect } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface PlanProgressModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

export const PlanProgressModal: React.FC<PlanProgressModalProps> = ({
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
      title="Agent sedang menyusun rencana"
      titleId="plan-progress-title"
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
            ✓ Membaca RPS dan preferensi
          </div>
          <div style={{ color: '#059669', fontWeight: 500 }}>
            ✓ Memetakan capaian pembelajaran
          </div>
          <div
            style={{
              color: progressStep >= 4 ? '#059669' : progressStep === 3 ? '#2563EB' : '#94A3B8',
              fontWeight: progressStep >= 3 ? 500 : 400,
            }}
          >
            {progressStep >= 4 ? '✓' : progressStep === 3 ? '●' : '○'} Menyusun 16 pertemuan
          </div>
          <div
            style={{
              color: isDone ? '#059669' : progressStep === 3 ? '#2563EB' : '#94A3B8',
              fontWeight: isDone ? 500 : progressStep === 3 ? 600 : 400,
            }}
          >
            {isDone
              ? '✓ Kesesuaian dengan RPS terverifikasi'
              : progressStep === 3
              ? '● Memvalidasi kesesuaian dengan RPS'
              : '○ Memvalidasi kesesuaian dengan RPS'}
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
            {isDone ? 'Lihat Course Plan' : 'Menyusun Rencana...'}
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
