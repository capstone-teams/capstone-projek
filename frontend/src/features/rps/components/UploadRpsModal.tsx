import React, { useState, useRef } from 'react'
import { ModalShell } from '../../../components/ui/ModalShell'

interface UploadRpsModalProps {
  isOpen: boolean
  onClose: () => void
  onStartAnalysis: () => void
}

export const UploadRpsModal: React.FC<UploadRpsModalProps> = ({
  isOpen,
  onClose,
  onStartAnalysis,
}) => {
  const [selectedFileName, setSelectedFileName] = useState('RPS_Keamanan_Siber.pdf')
  const [selectedFileSize, setSelectedFileSize] = useState('2.4 MB · Terverifikasi')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFileName(file.name)
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
      setSelectedFileSize(`${sizeMb} MB · Siap dianalisis`)
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      setSelectedFileName(file.name)
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
      setSelectedFileSize(`${sizeMb} MB · Siap dianalisis`)
    }
  }

  return (
    <ModalShell
      isOpen={isOpen}
      onClose={onClose}
      title="Upload RPS"
      titleId="upload-rps-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
            Dokumen RPS
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />
          <div
            style={{
              border: isDragging ? '2px dashed #2563EB' : '2px dashed #CBD5E1',
              borderRadius: '8px',
              padding: '28px 20px',
              textAlign: 'center',
              backgroundColor: isDragging ? '#EFF6FF' : '#F8FAFC',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                fileInputRef.current?.click()
              }
            }}
          >
            <div style={{ fontWeight: 600, color: '#1D4ED8', fontSize: '15px' }}>
              📄 {selectedFileName}
            </div>
            <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px' }}>
              {selectedFileSize}
            </div>
            <div
              style={{
                fontSize: '11px',
                color: '#2563EB',
                marginTop: '8px',
                fontWeight: 500,
              }}
            >
              Klik untuk memilih dokumen atau seret (drag & drop) file ke sini
            </div>
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
            onClick={onStartAnalysis}
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
            Upload & Analisis
          </button>
        </div>
      </div>
    </ModalShell>
  )
}
