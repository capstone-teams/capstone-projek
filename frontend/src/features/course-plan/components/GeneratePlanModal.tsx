import React, { useState } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface GeneratePlanModalProps {
  isOpen: boolean
  onClose: () => void
  onStartGenerate: () => void
}

export const GeneratePlanModal: React.FC<GeneratePlanModalProps> = ({
  isOpen,
  onClose,
  onStartGenerate,
}) => {
  const [approach, setApproach] = useState('Berbasis proyek dan studi kasus bertahap.')
  const [instructions, setInstructions] = useState(
    'Gunakan contoh kasus keamanan jaringan kampus.'
  )

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Generate Course Plan"
      titleId="generate-plan-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Pendekatan pembelajaran
          </label>
          <input
            type="text"
            value={approach}
            onChange={(e) => setApproach(e.target.value)}
            style={{
              padding: '10px 14px',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#0F172A',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Instruksi tambahan
          </label>
          <input
            type="text"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Gunakan contoh kasus keamanan jaringan kampus."
            style={{
              padding: '10px 14px',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#0F172A',
            }}
          />
        </div>

        <div style={{ fontSize: '13px', color: '#64748B', lineHeight: '1.5' }}>
          16 pertemuan berdasarkan RPS
          <br />
          Aktivitas: Materi · Resource · Tugas
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
            Batal
          </button>
          <button
            type="button"
            onClick={onStartGenerate}
            style={{
              backgroundColor: '#1D4ED8',
              color: '#FFFFFF',
              border: '1px solid #1D4ED8',
              borderRadius: '8px',
              padding: '10px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Mulai Generate
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
