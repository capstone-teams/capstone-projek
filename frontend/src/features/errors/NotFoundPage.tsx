import type { AppPath } from '../../types/navigation'
import { Button } from '../../components/ui/Button'
import { StatusPage } from './StatusPage'

interface NotFoundPageProps {
  homePath: AppPath
  onNavigate: (path: AppPath) => void
}

export function NotFoundPage({ homePath, onNavigate }: NotFoundPageProps) {
  return (
    <StatusPage
      code="404"
      title="Halaman tidak ditemukan"
      description="Alamat yang Anda buka tidak tersedia atau sudah dipindahkan. Periksa kembali tautan Anda atau kembali ke beranda."
      actions={<Button onClick={() => onNavigate(homePath)}>Kembali ke Beranda</Button>}
    />
  )
}
