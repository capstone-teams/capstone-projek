import React, { useState } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'
import type { UserProfile } from '../../../types/auth'
import { DOSEN_PROFILE } from '../../../types/auth'

interface ProfileModalProps {
  isOpen: boolean
  onClose: () => void
  profile?: UserProfile
  onSave?: (
    name: string,
    email: string,
    teachingApproach: string,
    aiInstructions: string
  ) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
  onResetDemo?: () => void
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  profile = DOSEN_PROFILE,
  onSave,
  onShowToast,
  onResetDemo,
}) => {
  const [profileName, setProfileName] = useState(profile.name)
  const [profileEmail, setProfileEmail] = useState(profile.email)
  const [teachingApproach, setTeachingApproach] = useState(
    profile.teachingApproach || 'Berbasis proyek dan studi kasus bertahap.'
  )
  const [aiInstructions, setAiInstructions] = useState(
    profile.aiInstructions ||
      'Gunakan contoh nyata penerapan aljabar linear pada komputasi dan grafika, sertakan latihan bertingkat, dan hindari kuis mendadak.'
  )

  const handleSave = () => {
    onSave?.(profileName, profileEmail, teachingApproach, aiInstructions)
    onShowToast?.('Profil dan preferensi AI dosen berhasil disimpan.', 'success')
    onClose()
  }

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Profil Dosen"
      titleId="profile-modal-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Nama Lengkap & Gelar</label>
          <input
            type="text"
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
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
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Email Institusi</label>
          <input
            type="email"
            value={profileEmail}
            onChange={(e) => setProfileEmail(e.target.value)}
            style={{
              padding: '10px 14px',
              border: '1px solid #CBD5E1',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#0F172A',
            }}
          />
        </div>

        <div
          style={{
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px' }}>🤖</span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B' }}>
              Preferensi & Instruksi AI Agent
            </span>
          </div>
          <p style={{ fontSize: '12px', color: '#64748B', margin: 0, lineHeight: 1.4 }}>
            Instruksi dan preferensi ini otomatis digunakan oleh Agent AI saat menyusun Course Plan maupun modul mingguan.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Pendekatan Pembelajaran
            </label>
            <input
              type="text"
              value={teachingApproach}
              onChange={(e) => setTeachingApproach(e.target.value)}
              placeholder="Misal: Berbasis proyek dan studi kasus bertahap."
              style={{
                padding: '8px 12px',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                fontSize: '13px',
                color: '#0F172A',
                backgroundColor: '#FFFFFF',
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Instruksi Tambahan AI
            </label>
            <textarea
              rows={3}
              value={aiInstructions}
              onChange={(e) => setAiInstructions(e.target.value)}
              placeholder="Contoh: Gunakan kasus nyata aplikasi komputasi, sediakan latihan bertingkat..."
              style={{
                padding: '8px 12px',
                border: '1px solid #CBD5E1',
                borderRadius: '6px',
                fontSize: '13px',
                color: '#0F172A',
                fontFamily: 'inherit',
                backgroundColor: '#FFFFFF',
              }}
            />
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
            Batal
          </button>
          <button
            type="button"
            onClick={handleSave}
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
            Simpan
          </button>
        </div>

        {onResetDemo && (
          <div
            style={{
              borderTop: '1px solid #E2E8F0',
              paddingTop: '16px',
              marginTop: '4px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
                Reset Alur Demo
              </div>
              <div style={{ fontSize: '12px', color: '#64748B' }}>
                Kembalikan status mata kuliah dan materi ke kondisi awal (kosong).
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                onResetDemo()
                onClose()
              }}
              style={{
                backgroundColor: '#FEF2F2',
                color: '#DC2626',
                border: '1px solid #FECACA',
                borderRadius: '6px',
                padding: '8px 14px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Reset Alur Demo
            </button>
          </div>
        )}
      </div>
    </ModalShell>
  )
}
