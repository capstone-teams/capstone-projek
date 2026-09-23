import React, { useState } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'
import { DOSEN_PROFILE } from '../../../types/auth'

interface ProfileModalProps {
  isOpen: boolean
  onClose: () => void
  onSave?: (name: string, email: string, preference: string) => void
  onShowToast?: (message: string, type?: 'info' | 'success') => void
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  onSave,
  onShowToast,
}) => {
  const [profileName, setProfileName] = useState(DOSEN_PROFILE.name)
  const [profileEmail, setProfileEmail] = useState(DOSEN_PROFILE.email)
  const [profilePref, setProfilePref] = useState(
    'Studi kasus praktis dan tugas berbasis simulasi.'
  )

  const handleSave = () => {
    onSave?.(profileName, profileEmail, profilePref)
    onShowToast?.('Profil dosen berhasil diperbarui.', 'success')
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
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Nama</label>
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
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Email</label>
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

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Preferensi Mengajar
          </label>
          <textarea
            rows={3}
            value={profilePref}
            onChange={(e) => setProfilePref(e.target.value)}
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
      </div>
    </ModalShell>
  )
}
