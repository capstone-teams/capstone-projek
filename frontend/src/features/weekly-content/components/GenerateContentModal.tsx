import React, { useState } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface GenerateContentModalProps {
  isOpen: boolean
  onClose: () => void
  onStartGenerate: () => void
}

export const GenerateContentModal: React.FC<GenerateContentModalProps> = ({
  isOpen,
  onClose,
  onStartGenerate,
}) => {
  const [instructions, setInstructions] = useState(
    'Sertakan latihan analisis jejak digital pada lingkungan simulasi.'
  )

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Generate Konten Mingguan"
      titleId="generate-content-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Pertemuan
          </label>
          <input
            type="text"
            value="Minggu 03 · Rekognisi Jejak Digital"
            disabled
            style={{
              padding: '10px 14px',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#64748B',
              backgroundColor: '#F1F5F9',
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
            placeholder="Sertakan latihan analisis jejak digital pada lingkungan simulasi."
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
          Konten: Materi · Resource · Tugas
          <br />
          Kuis tidak disertakan
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
