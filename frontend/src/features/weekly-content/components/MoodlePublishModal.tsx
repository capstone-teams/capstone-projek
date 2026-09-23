import React from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface MoodlePublishModalProps {
  isOpen: boolean
  onClose: () => void
  onExecute: () => void
}

export const MoodlePublishModal: React.FC<MoodlePublishModalProps> = ({
  isOpen,
  onClose,
  onExecute,
}) => {
  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Execute ke Moodle"
      titleId="moodle-publish-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Course tujuan
          </label>
          <input
            type="text"
            value="Keamanan Siber · Kelas A"
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

        <div style={{ fontSize: '13px', color: '#64748B', lineHeight: '1.5' }}>
          Konten disetujui · Versi 1
          <br />
          Materi · Resource · Tugas
          <br />
          Hasil pengiriman akan diperiksa kembali di Moodle.
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
            onClick={onExecute}
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
            Execute ke Moodle
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
