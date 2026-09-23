import React, { useState } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface ContentRevisionModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmitRevision: (section: string, notes: string) => void
}

export const ContentRevisionModal: React.FC<ContentRevisionModalProps> = ({
  isOpen,
  onClose,
  onSubmitRevision,
}) => {
  const [section, setSection] = useState('Materi Pembelajaran')
  const [notes, setNotes] = useState(
    'Tambahkan contoh studi kasus dan ringkasan langkah praktik.'
  )

  const handleSubmit = () => {
    onSubmitRevision(section, notes)
  }

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Minta Revisi Konten"
      titleId="content-revision-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Bagian yang direvisi
          </label>
          <input
            type="text"
            value={section}
            onChange={(e) => setSection(e.target.value)}
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
            Catatan revisi
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Tambahkan contoh studi kasus dan ringkasan langkah praktik."
            style={{
              padding: '10px 14px',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#0F172A',
              fontFamily: 'inherit',
            }}
          />
        </div>

        <div style={{ fontSize: '13px', color: '#64748B' }}>
          Bagian lain tetap menggunakan versi yang sudah ada.
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
            onClick={handleSubmit}
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
            Kirim Revisi
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
